#!/usr/bin/env python
# Stop hook：session 結束時，若 harness repo 的 skills/、agents/ 或 local-plugins/ 有變動，
# 掃描 staged 內容的秘鑰指紋後自動 commit + push，讓 stan-claude-harness 保持最新。
#
# 安全紀律：
#   - 偵測到疑似秘鑰 → fail-closed：unstage、明顯告警、絕不 commit/push。
#   - git 操作失敗（網路 / 並行 session 衝突）→ fail-open：告警但不卡 session。
#   - 只碰 skills/、agents/、local-plugins/，其餘變動一律不動。
#   - 任何未預期例外都 exit 0，收尾不受影響。
#
# gitleaks 第二層掃描（自製指紋掃描之後、commit 之前執行，只掃 staged 內容）：
#   - 開關：環境變數 HARNESS_GITLEAKS_MODE
#       observe（預設；未設定或值無法辨識都算 observe）：有發現只寫 log 並告警，commit/push 決定不變。
#       enforce：有發現就走上面同一套 fail-closed（unstage、告警、不 commit 不 push）。
#   - gitleaks 找不到、逾時（30 秒）或出錯 → fail-open：記一筆失敗、告警，照原本流程走。
#   - 紀錄檔：本檔同目錄的 harness-autosync.log（每行一筆 JSON），只記時間、檔名、規則 ID、行號。
#   - 一律帶 --redact=100，報告只取檔名、規則 ID、行號三欄，秘鑰原文不進 log 也不進 stderr。
import sys, os, re, json, shutil, subprocess
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WATCH = ["skills", "agents", "local-plugins"]

# 高信度秘鑰指紋：命中幾乎必為真秘鑰，不用泛型 key=value（會誤報講解文字）。
SECRET_PATTERNS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
]


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")


def paths_present():
    return [p for p in WATCH if os.path.isdir(os.path.join(REPO, p))]


def scan_staged():
    """回傳 [(檔案, 指紋名)]，只掃新增行；不回傳命中的字串本身，避免把秘鑰寫進 log。"""
    diff = git("diff", "--cached", "--unified=0")
    if diff.returncode != 0:
        return []
    hits, cur = [], "?"
    for line in diff.stdout.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for name, pat in SECRET_PATTERNS:
            if pat.search(line):
                hits.append((cur, name))
    return hits


def warn(msg):
    sys.stderr.write(f"\n[harness-autosync] {msg}\n")


GITLEAKS_TIMEOUT = 30    # 秒，整個 gitleaks 子程序的上限
GITLEAKS_LEAK_EXIT = 77  # 自訂「有發現」退出碼；gitleaks 出錯時退出碼是 1，兩者才分得開
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harness-autosync.log")


def gitleaks_mode():
    """回傳 (模式, 無法辨識的原值或 None)。只有明確寫 enforce 才擋，其餘一律 observe。"""
    raw = os.environ.get("HARNESS_GITLEAKS_MODE", "").strip().lower()
    if raw in ("", "observe"):
        return "observe", None
    if raw == "enforce":
        return "enforce", None
    return "observe", raw


def find_gitleaks():
    found = shutil.which("gitleaks")
    if found:
        return found
    # hook 的 PATH 可能沒帶 winget 的 Links 目錄，補查 winget 預設安裝位置
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cand = os.path.join(local, "Microsoft", "WinGet", "Links", "gitleaks.exe")
        if os.path.isfile(cand):
            return cand
    return None


def log_event(event, **fields):
    """寫一筆 JSON 到 LOG_PATH；寫不進去就算了，不能影響同步。"""
    rec = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def run_gitleaks():
    """對 staged 內容跑 gitleaks，回傳 (findings, error)。
    findings 是 [(檔名, 規則 ID, 行號)]；error 是失敗原因，None 表示有正常跑完。
    報告裡的 Secret、Match 等欄位已遮蔽，但這裡仍只取三個欄位，stderr 也不讀。"""
    exe = find_gitleaks()
    if not exe:
        return [], "找不到 gitleaks 執行檔"
    cmd = [
        exe, "git", "--pre-commit", "--staged",
        "--redact=100", "--no-banner", "--no-color", "--log-level", "error",
        "--report-format", "json", "--report-path", "-",
        "--exit-code", str(GITLEAKS_LEAK_EXIT),
        "--timeout", str(GITLEAKS_TIMEOUT - 5),
        REPO,
    ]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=GITLEAKS_TIMEOUT)
    except subprocess.TimeoutExpired:
        return [], f"逾時，超過 {GITLEAKS_TIMEOUT} 秒"
    except OSError as e:
        return [], f"無法執行 gitleaks：{type(e).__name__}"
    if r.returncode == 0:
        return [], None
    if r.returncode != GITLEAKS_LEAK_EXIT:
        return [], f"gitleaks 退出碼 {r.returncode}"
    findings = []
    try:
        for f in json.loads(r.stdout or "[]"):
            findings.append((str(f.get("File", "?")), str(f.get("RuleID", "?")), str(f.get("StartLine", "?"))))
    except Exception:
        findings = []
    # 退出碼已表示有發現，報告解析不了也要算一筆，enforce 時才不會因此放行
    return findings or [("?", "report-unparsed", "?")], None


def gitleaks_gate():
    """第二層 gitleaks 閘門。回傳要擋下的 findings；空 list 代表照原流程繼續。
    只有 enforce 模式且有發現才回非空；任何失敗都回空 list（fail-open）。"""
    try:
        mode, bad = gitleaks_mode()
        if bad is not None:
            log_event("gitleaks-bad-mode", value=bad[:40], used="observe")
            warn(f"HARNESS_GITLEAKS_MODE={bad[:40]} 無法辨識，本次以 observe 執行。")
        findings, err = run_gitleaks()
        if err:
            log_event("gitleaks-failed", mode=mode, reason=err)
            warn(f"gitleaks 第二層掃描沒有跑成（{err}），照原流程繼續；已記錄到 {LOG_PATH}")
            return []
        if not findings:
            return []
        log_event("gitleaks-findings", mode=mode, count=len(findings),
                  action="block" if mode == "enforce" else "continue",
                  findings=[{"file": f, "rule": r, "line": ln} for f, r, ln in findings])
        if mode == "enforce":
            return findings
        warn(f"gitleaks 觀察模式發現 {len(findings)} 筆，這次照舊 push，請檢查：")
        for f, r, ln in findings[:10]:
            warn(f"  - {r} @ {f}:{ln}")
        if len(findings) > 10:
            warn(f"  另有 {len(findings) - 10} 筆，見紀錄檔")
        warn(f"紀錄檔：{LOG_PATH}")
        return []
    except Exception as e:
        log_event("gitleaks-failed", reason=f"未預期例外（{type(e).__name__}）")
        warn(f"gitleaks 第二層掃描發生未預期例外（{type(e).__name__}），照原流程繼續。")
        return []


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass

    if not os.path.isdir(os.path.join(REPO, ".git")):
        return

    watched = paths_present()
    if not watched:
        return

    status = git("status", "--porcelain", "--", *watched)
    if status.returncode != 0 or not status.stdout.strip():
        return  # 無變動，靜默收尾

    add = git("add", "--", *watched)
    if add.returncode != 0:
        warn(f"git add 失敗，略過本次同步：{add.stderr.strip()}")
        return

    if git("diff", "--cached", "--quiet", "--", *watched).returncode == 0:
        return  # add 後其實沒有 staged 內容

    hits = scan_staged()
    if hits:
        git("reset", "-q", "HEAD", "--", *watched)
        uniq = sorted(set(hits))
        warn("偵測到疑似秘鑰，已中止自動同步（未 commit、未 push）：")
        for f, n in uniq:
            warn(f"  - {n} @ {f}")
        warn("若為誤報，請自行檢視後手動 commit/push；若確為秘鑰，先移出追蹤並輪換。")
        return

    blocked = gitleaks_gate()
    if blocked:
        git("reset", "-q", "HEAD", "--", *watched)
        warn("gitleaks（enforce 模式）偵測到疑似秘鑰，已中止自動同步（未 commit、未 push）：")
        for f, r, ln in sorted(set(blocked)):
            warn(f"  - {r} @ {f}:{ln}")
        warn("若為誤報，請自行檢視後手動 commit/push；若確為秘鑰，先移出追蹤並輪換。")
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = git("commit", "-m", f"chore(harness): auto-sync skills/agents/local-plugins at session end ({ts})")
    if commit.returncode != 0:
        warn(f"git commit 失敗，略過本次同步：{commit.stderr.strip() or commit.stdout.strip()}")
        return

    push = git("push")
    if push.returncode != 0:
        warn("已本地 commit，但 push 失敗（可能網路或並行 session 衝突）。請手動 `git -C ~/.claude push`。")
        warn(f"  git 訊息：{push.stderr.strip()}")
        return

    sys.stderr.write(f"\n[harness-autosync] 已同步 skills/agents/local-plugins 變動到 harness repo（{ts}）。\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        warn(f"未預期錯誤，已略過（不影響收尾）：{e}")
    sys.exit(0)
