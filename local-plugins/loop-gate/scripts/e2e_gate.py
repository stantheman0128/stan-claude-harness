"""loop-gate e2e gate：改了一定量的程式碼，卻沒實際跑過改到的流程時，先記錄、之後可以擋下。

內建 /verify 只有使用者能打，模型和 hook 都叫不到，所以這支只檢查 session 裡有沒有做過等價的驗證。

用法（由 hooks.json 呼叫）：
  py e2e_gate.py --event session-start   記下 session 起點的 repo 與 HEAD
  py e2e_gate.py --event stop            收工前檢查改動量與驗證證據
  py e2e_gate.py --event pre-bash        git commit 要有 Verified 行，gh pr create 要先 code-review

模式與門檻寫在下方 DEFAULTS，可用 state_dir()/e2e_gate.json 覆寫：
  {"mode": "observe" | "enforce" | "off", "min_lines": 40, "min_files": 3,
   "skip_commit_roots": ["C:\\Users\\stans\\Projects\\oss"]}
所有例外都 fail-open：hook_health.guard 記錄後 exit 0。
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

import hook_health

DEFAULTS = {
    "mode": "observe",
    "min_lines": 40,
    "min_files": 3,
    "skip_commit_roots": [r"C:\Users\stans\Projects\oss"],
}
MODES = ("observe", "enforce", "off")
MAX_BLOCKS = 2
SESSION_TTL_SEC = 7 * 24 * 3600
MAX_UNTRACKED_BYTES = 2_000_000
MAX_LOG_BYTES = 2_000_000

DOC_SUFFIXES = {".md", ".mdx", ".txt", ".rst"}
TEST_DIRS = {"tests", "test", "__tests__"}
LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "bun.lockb", "poetry.lock", "pipfile.lock", "uv.lock", "pdm.lock",
    "cargo.lock", "composer.lock", "gemfile.lock", "go.sum", "packages.lock.json",
    "flake.lock",
}

COMMIT_RE = re.compile(r"\bgit(?:\s+-[cC]\s+(?:\"[^\"]*\"|'[^']*'|\S+))*\s+commit\b")
PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")
VERIFY_SKILL_REL = ".claude/skills/verify/SKILL.md"

STOP_REASON = (
    "[loop-gate e2e] 這次改了 {lines} 行程式碼（{files} 個檔），還沒實際跑過改到的流程。"
    "照 .claude/skills/verify/SKILL.md 實際跑一遍改到的流程，沒有這個檔就用 run skill；"
    "真的不適用，就在最後回覆寫一行 `Verified: none（理由）`。")
OBSERVE_NOTICE = (
    "[loop-gate e2e] 這次改了 {lines} 行程式碼，還沒實際跑過改到的流程；"
    "這個專案還沒有 verify skill，下次在這裡打 /verify 建一份。")
COMMIT_REASON = (
    "[loop-gate e2e] commit 訊息要有一行 `Verified: <怎麼驗的>`，"
    "沒有實際驗證就寫 `Verified: none（理由）`。")
PR_REASON = "[loop-gate e2e] 開 PR 前先跑 /code-review、/simplify。"


# ---------- 設定與狀態 ----------

def load_config():
    cfg = dict(DEFAULTS)
    try:
        override = json.loads((hook_health.state_dir() / "e2e_gate.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        override = {}
    if not isinstance(override, dict):
        override = {}
    if override.get("mode") in MODES:
        cfg["mode"] = override["mode"]
    for k in ("min_lines", "min_files"):
        if isinstance(override.get(k), int) and override[k] >= 0:
            cfg[k] = override[k]
    if isinstance(override.get("skip_commit_roots"), list):
        cfg["skip_commit_roots"] = [str(x) for x in override["skip_commit_roots"]]
    return cfg


def sessions_path():
    return hook_health.state_dir() / "e2e_sessions.json"


def load_sessions():
    try:
        data = json.loads(sessions_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        return {}
    now = time.time()
    return {k: v for k, v in data.items()
            if isinstance(v, dict) and isinstance(v.get("ts"), (int, float))
            and now - v["ts"] <= SESSION_TTL_SEC}


def save_sessions(data):
    sessions_path().write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def append_log(record):
    path = hook_health.state_dir() / "e2e-gate.jsonl"
    hook_health._rotate(path, MAX_LOG_BYTES)
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------- git ----------

def _git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", str(cwd), *args],
                             capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", errors="replace")


def repo_root(cwd):
    if not cwd or not Path(cwd).is_dir():
        return None
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(top.strip()).resolve() if top and top.strip() else None


def head_of(root):
    out = _git(root, "rev-parse", "--verify", "-q", "HEAD")
    return out.strip() if out and out.strip() else None


def is_code_file(rel):
    p = PurePosixPath(rel.replace("\\", "/").lower())
    name = p.name
    dirs = set(p.parts[:-1])
    if p.suffix in DOC_SUFFIXES or "docs" in dirs:
        return False
    if dirs & TEST_DIRS:
        return False
    if (name.startswith("test_") and name.endswith(".py")) \
            or re.search(r"_test\.[^.]+$", name) \
            or re.search(r"\.(test|spec)\.[^.]+$", name):
        return False
    if name in LOCKFILES or name.endswith(".lock"):
        return False
    if rel.replace("\\", "/").endswith(".claude/loop-gate-evidence.json"):
        return False
    return True


def _parse_numstat(text):
    """解析 `--numstat -z` 輸出；binary（-\t-）略過。回傳 {path: 行數}。"""
    counts = {}
    for chunk in (text or "").split("\0"):
        parts = chunk.split("\t", 2)
        if len(parts) != 3 or not parts[2]:
            continue
        added, deleted, path = parts
        if added == "-" or deleted == "-":
            continue
        try:
            counts[path] = int(added) + int(deleted)
        except ValueError:
            continue
    return counts


def _untracked_lines(path):
    try:
        if path.stat().st_size > MAX_UNTRACKED_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None  # binary
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def count_changes(root, base):
    """回傳（程式碼行數, 程式碼檔數），只算 is_code_file 為真的檔。"""
    counts = {}
    diff = _git(root, "diff", "--numstat", "-z", "--no-renames", base) if base else None
    if diff is None and base:
        base = None
    if base is None:
        # 沒有 HEAD 的新 repo：只看暫存區
        diff = _git(root, "diff", "--cached", "--numstat", "-z", "--no-renames") or ""
    counts.update(_parse_numstat(diff))
    others = _git(root, "ls-files", "--others", "--exclude-standard", "-z") or ""
    for rel in others.split("\0"):
        if rel and rel not in counts:
            n = _untracked_lines(root / rel)
            if n is not None:
                counts[rel] = n
    code = {p: n for p, n in counts.items() if is_code_file(p) and n > 0}
    return sum(code.values()), len(code)


# ---------- transcript 證據 ----------

def _user_texts(content):
    """只取使用者自己打的文字；tool_result 裡的字串不算。"""
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"]
    return []


def scan_transcript(path):
    """掃 transcript JSONL，回傳 tool 呼叫、使用者指令文字、最後一則 assistant 文字。"""
    tool_uses, user_texts, last_text = [], [], None
    if not path:
        return tool_uses, user_texts, last_text
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return tool_uses, user_texts, last_text
    with f:
        for line in f:
            if "tool_use" not in line and "<command-name>" not in line \
                    and "assistant" not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            msg = entry.get("message") if isinstance(entry, dict) else None
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if entry.get("type") == "user":
                user_texts.extend(t for t in _user_texts(content) if "<command-name>" in t)
            elif entry.get("type") == "assistant" and isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        tool_uses.append((b.get("name"), b.get("input") or {}))
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        last_text = b["text"]
    return tool_uses, user_texts, last_text


def has_verified_line(text):
    return any(line.strip().startswith("Verified:") for line in (text or "").splitlines())


def verified(event, scan):
    tool_uses, user_texts, last_text = scan
    for name, inp in tool_uses:
        if not isinstance(inp, dict):
            continue
        if name == "Skill":
            skill = str(inp.get("skill", ""))
            if skill in ("run", "verify") or skill.endswith(":verify"):
                return True
        elif name in ("Agent", "Task") and inp.get("subagent_type") == "verifier":
            return True
        elif name == "Read" and str(inp.get("file_path", "")).replace("\\", "/").endswith(VERIFY_SKILL_REL):
            return True
    if any("<command-name>/verify</command-name>" in t for t in user_texts):
        return True
    # transcript 在 Stop 當下可能還沒寫到最後一則，官方建議優先用 last_assistant_message
    final = event.get("last_assistant_message")
    if not isinstance(final, str) or not final.strip():
        final = last_text
    return has_verified_line(final)


def code_reviewed(scan):
    tool_uses, user_texts, _ = scan
    for name, inp in tool_uses:
        if name == "Skill" and isinstance(inp, dict) and inp.get("skill") == "code-review":
            return True
    return any("<command-name>/code-review</command-name>" in t for t in user_texts)


# ---------- 三種事件 ----------

def on_session_start(event, cfg):
    root = repo_root(event.get("cwd"))
    sessions = load_sessions()
    sid = str(event.get("session_id", ""))
    if root is not None and sid and sid not in sessions:
        # resume 時已有紀錄就保留原本的基準，不要被目前 HEAD 蓋掉
        sessions[sid] = {"repo": str(root), "head": head_of(root), "ts": time.time()}
    save_sessions(sessions)


def on_stop(event, cfg):
    if event.get("stop_hook_active"):
        return
    root = repo_root(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR"))
    if root is None:
        return
    sid = str(event.get("session_id", "unknown"))
    sessions = load_sessions()
    rec = sessions.get(sid)
    base = None
    if rec and rec.get("head") and Path(rec.get("repo", "")) == root:
        base = rec["head"]
    base = base or head_of(root)
    lines, files = count_changes(root, base)
    if lines < cfg["min_lines"] and files < cfg["min_files"]:
        return
    if verified(event, scan_transcript(event.get("transcript_path"))):
        return

    has_skill = (root / VERIFY_SKILL_REL).is_file()
    append_log({"event": "stop", "mode": cfg["mode"], "session": sid, "repo": str(root),
                "lines": lines, "files": files, "has_verify_skill": has_skill,
                "would_block": True})

    if cfg["mode"] == "enforce":
        rec = sessions.setdefault(sid, {"repo": str(root), "head": base, "ts": time.time()})
        blocks = int(rec.get("blocks", 0))
        if blocks < MAX_BLOCKS:
            rec["blocks"] = blocks + 1
            save_sessions(sessions)
            hook_health.emit_json({"decision": "block",
                                   "reason": STOP_REASON.format(lines=lines, files=files)})
        return  # 第三次起放行，避免卡死

    if not has_skill and hook_health.once_per_session("e2e-no-verify-skill", sid, str(root)):
        hook_health.emit_json({"systemMessage": OBSERVE_NOTICE.format(lines=lines)})


def _under(path, prefix):
    p = os.path.normcase(os.path.abspath(str(path)))
    pre = os.path.normcase(os.path.abspath(prefix)).rstrip("\\/")
    return p == pre or p.startswith(pre + os.sep)


def _deny(reason):
    hook_health.emit_json({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }})


def on_pre_bash(event, cfg):
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return
    is_commit = bool(COMMIT_RE.search(command)) and "Verified:" not in command
    is_pr = bool(PR_CREATE_RE.search(command))
    if not is_commit and not is_pr:
        return
    cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or ""
    root = repo_root(cwd) or (Path(cwd) if cwd else None)
    sid = str(event.get("session_id", "unknown"))

    if is_commit and root is not None \
            and any(_under(root, pre) for pre in cfg["skip_commit_roots"]):
        is_commit = False  # OSS 照上游 commit 慣例
    if is_pr and code_reviewed(scan_transcript(event.get("transcript_path"))):
        is_pr = False

    for flag, check, reason in ((is_commit, "commit-without-verified", COMMIT_REASON),
                                (is_pr, "pr-without-code-review", PR_REASON)):
        if not flag:
            continue
        append_log({"event": "pre-bash", "mode": cfg["mode"], "session": sid,
                    "repo": str(root) if root else "", "check": check, "would_block": True})
        if cfg["mode"] == "enforce":
            _deny(reason)
            return


HANDLERS = {"session-start": on_session_start, "stop": on_stop, "pre-bash": on_pre_bash}


def main():
    args = sys.argv[1:]
    name = args[args.index("--event") + 1] if "--event" in args[:-1] else None
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    handler = HANDLERS.get(name)
    if handler is None:
        hook_health.log_failure("e2e_gate", f"未知的 --event：{name!r}")
        sys.exit(0)
    cfg = load_config()
    if cfg["mode"] == "off":
        sys.exit(0)
    handler(event, cfg)
    sys.exit(0)


if __name__ == "__main__":
    hook_health.guard("e2e_gate", main)
