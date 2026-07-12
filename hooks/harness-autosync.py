#!/usr/bin/env python
# Stop hook：session 結束時，若 harness repo 的 skills/ 或 agents/ 有變動，
# 掃描 staged 內容的秘鑰指紋後自動 commit + push，讓 stan-claude-harness 保持最新。
#
# 安全紀律：
#   - 偵測到疑似秘鑰 → fail-closed：unstage、明顯告警、絕不 commit/push。
#   - git 操作失敗（網路 / 並行 session 衝突）→ fail-open：告警但不卡 session。
#   - 只碰 skills/ 與 agents/，其餘變動一律不動。
#   - 任何未預期例外都 exit 0，收尾不受影響。
import sys, os, re, json, subprocess
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WATCH = ["skills", "agents"]

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

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = git("commit", "-m", f"chore(harness): auto-sync skills/agents at session end ({ts})")
    if commit.returncode != 0:
        warn(f"git commit 失敗，略過本次同步：{commit.stderr.strip() or commit.stdout.strip()}")
        return

    push = git("push")
    if push.returncode != 0:
        warn("已本地 commit，但 push 失敗（可能網路或並行 session 衝突）。請手動 `git -C ~/.claude push`。")
        warn(f"  git 訊息：{push.stderr.strip()}")
        return

    sys.stderr.write(f"\n[harness-autosync] 已同步 skills/agents 變動到 harness repo（{ts}）。\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        warn(f"未預期錯誤，已略過（不影響收尾）：{e}")
    sys.exit(0)
