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
MAX_MSG_BYTES = 1_000_000

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


# ---------- pre-bash：git commit 實際 commit 到哪、訊息從哪來 ----------
# Bash 工具在這台機器是 Git Bash，所以照 bash 的引號與跳脫規則切指令。
# 任何一步判斷不出來就回 None（不知道），不記也不擋。

_OPS = ("<<<", "&&", "||", ";;", "|&", ">>", "<<", ">&", "<&", "&>", ">|", "<>",
        ";", "&", "|", "(", ")", "<", ">", "\n")
_REDIR_OPS = {"<<<", ">>", "<<", ">&", "<&", "&>", ">|", "<>", "<", ">"}
_HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([^\s;&|<>()'\"]+))")
_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_MSYS_DRIVE_RE = re.compile(r"/([A-Za-z])(?=/|$)")
_PREFIX_WORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "}",
                 "fi", "done", "time", "command", "builtin", "exec", "nohup", "env"}
_GIT_GLOBAL_ARG = {"-c", "--namespace", "--super-prefix", "--config-env", "--attr-source"}
_COMMIT_SHORT_ARG = set("mFCct")    # 後面接參數（同一串或下一個字）
_COMMIT_SHORT_OPTARG = set("uS")    # 參數只能黏在後面
_COMMIT_LONG_ARG = {"--message": "m", "--file": "F", "--reuse-message": "C",
                    "--reedit-message": "c", "--fixup": "fixup", "--squash": "fixup",
                    "--template": None, "--author": None, "--date": None, "--cleanup": None,
                    "--trailer": None, "--pathspec-from-file": None}


def _strip_heredocs(command):
    """拿掉 heredoc 內文（內文什麼字元都可能有，會弄壞斷詞）。

    回傳（拿掉後的指令, 內文會不會被 bash 展開：delimiter 沒加引號而且內文含 $ 或 `）。
    """
    lines, out, expanding, i = command.split("\n"), [], False, 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in _HEREDOC_RE.finditer(line):
            dash, quoted = m.group(1), m.group(2) is not None or m.group(3) is not None or m.group(4)
            delim = next(g for g in (m.group(2), m.group(3), m.group(5)) if g is not None)
            body = []
            while i < len(lines):
                cur = lines[i].rstrip("\r")
                i += 1
                if (cur.lstrip("\t") if dash else cur) == delim:
                    break
                body.append(cur)
            if not quoted and any("$" in b or "`" in b for b in body):
                expanding = True
    return "\n".join(out), expanding


def _expansion(s, i):
    """s[i] 是 $ 或 `：回傳（下一個位置, 原文, 是否真的會展開）。沒收尾丟 ValueError。"""
    n = len(s)
    if s[i] == "`":
        j = i + 1
        while j < n and s[j] != "`":
            j += 2 if s[j] == "\\" else 1
        if j >= n:
            raise ValueError("unterminated `")
        return j + 1, s[i:j + 1], True
    nxt = s[i + 1] if i + 1 < n else ""
    if nxt == "(":
        depth, j = 0, i + 1
        while j < n:
            ch = s[j]
            if ch == "\\":
                j += 2
                continue
            if ch == "'":
                j = s.index("'", j + 1) + 1
                continue
            if ch == '"':
                j += 1
                while j < n and s[j] != '"':
                    j += 2 if s[j] == "\\" else 1
                j += 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return j + 1, s[i:j + 1], True
            j += 1
        raise ValueError("unterminated $(")
    if nxt == "{":
        j = s.index("}", i)
        return j + 1, s[i:j + 1], True
    if nxt and (nxt.isalnum() or nxt in "_?!#@*$-"):
        j = i + 2
        if nxt.isalpha() or nxt == "_":
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
        return j, s[i:j], True
    return i + 1, "$", False


def _shell_tokens(s):
    """切成 ("w", 文字, 值不確定, 開頭是沒引號的 ~) 與 ("op", 運算子)。引號沒收尾丟 ValueError。

    值不確定：含 $ 展開、反引號、萬用字元，或沒加引號的反斜線。
    """
    toks, i, n = [], 0, len(s)
    word, unsafe, tilde, in_word = [], False, False, False

    def flush(keep=True):
        nonlocal word, unsafe, tilde, in_word
        if in_word and keep:
            toks.append(("w", "".join(word), unsafe, tilde))
        word, unsafe, tilde, in_word = [], False, False, False

    while i < n:
        c = s[i]
        if c in " \t\r":
            flush()
            i += 1
        elif c == "#" and not in_word:
            while i < n and s[i] != "\n":
                i += 1
        elif c == "\\":
            if s.startswith("\\\n", i):
                i += 2  # 續行
                continue
            # Bash 工具送進 bash 前會先把 \\ 變成 \，沒加引號的反斜線最後變成什麼不確定
            word.append(s[i + 1:i + 2])
            unsafe = in_word = True
            i += 2
        elif c == "'":
            j = s.index("'", i + 1)
            word.append(s[i + 1:j])
            in_word = True
            i = j + 1
        elif c == '"':
            in_word = True
            i += 1
            while True:
                if i >= n:
                    raise ValueError('unterminated "')
                c = s[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and s[i + 1] in '"\\$`\n':
                    if s[i + 1] != "\n":
                        word.append(s[i + 1])
                    i += 2
                elif c in "$`":
                    i, part, exp = _expansion(s, i)
                    word.append(part)
                    unsafe |= exp
                else:
                    word.append(c)
                    i += 1
        elif c in "$`":
            in_word = True
            i, part, exp = _expansion(s, i)
            word.append(part)
            unsafe |= exp
        elif c in ";&|()<>\n":
            # 2>/dev/null 的 2 是檔案代號，不是參數
            flush(keep=not (c in "<>" and in_word and not unsafe and "".join(word).isdigit()))
            op = next(o for o in _OPS if s.startswith(o, i))
            toks.append(("op", op))
            i += len(op)
        else:
            if c == "~" and not in_word:
                tilde = True
            if c in "*?[":
                unsafe = True
            word.append(c)
            in_word = True
            i += 1
    flush()
    return toks


def _to_path(word, base):
    """把一個 word 轉成 Windows 路徑；相對路徑接在 base 後面。轉不出來回 None。"""
    _, text, unsafe, tilde = word
    if unsafe:
        return None
    if tilde:
        if text != "~" and not text.startswith(("~/", "~\\")):
            return None  # ~user
        text = str(Path.home()) + text[1:]
    m = _MSYS_DRIVE_RE.match(text)
    if m:
        text = m.group(1).upper() + ":" + (text[2:] or "/")  # /c/Users → C:/Users
    elif text.startswith(("/", "\\")):
        return None  # /tmp、/usr 對到哪只有 MSYS 知道
    elif re.match(r"[A-Za-z]:(?![\\/])", text):
        return None  # C:foo 是磁碟相對路徑
    p = Path(text)
    if p.is_absolute():
        return p
    return base / p if base is not None else None


def _cd_target(args, cur):
    a = list(args)
    while a and a[0][1] in ("-L", "-P", "-e", "-@"):
        a.pop(0)
    if a and a[0][1] == "--":
        a.pop(0)
    if len(a) == 2 and a[0][1].lower() == "/d":
        a.pop(0)  # cmd 的 cd /d
    if not a:
        return _to_path(("w", "~", False, True), cur)
    if len(a) != 1 or a[0][1] == "-":
        return None
    return _to_path(a[0], cur)


def _git_commit_args(args, cur):
    """args 是 git 後面的 words：是 git commit 就回（git 實際跑的資料夾或 None, commit 的參數），不是回 None。"""
    d, i = cur, 0
    while i < len(args):
        t = args[i][1]
        if t == "-C" and i + 1 < len(args):
            if args[i + 1][1] != "":  # git -C "" 不換資料夾
                d = _to_path(args[i + 1], d)
            i += 2
        elif t in ("--git-dir", "--work-tree"):
            d, i = None, i + 2  # 指到別處的 repo，不猜
        elif t.startswith(("--git-dir=", "--work-tree=")):
            d, i = None, i + 1
        elif t in _GIT_GLOBAL_ARG:
            i += 2  # git -c key=val 是全域設定，不是 commit 的 -c
        elif t.startswith("-"):
            i += 1
        else:
            return (d, args[i + 1:]) if t == "commit" else None
    return None


def _git_commits(command, cwd):
    """找出指令裡每一個 git commit，回傳 [(資料夾或 None, commit 參數, 同一段有 heredoc, heredoc 會展開)]。"""
    stripped, expanding = _strip_heredocs(command)
    toks = _shell_tokens(stripped) + [("op", "\n")]
    cur = Path(cwd) if cwd else None
    stack, found, seg, prev = [], [], [], None
    heredoc = skip_next = False
    for tok in toks:
        if tok[0] == "w":
            if skip_next:
                skip_next = False  # 重新導向的目標
            else:
                seg.append(tok)
            continue
        op = tok[1]
        if op in _REDIR_OPS:
            heredoc |= op == "<<"
            skip_next = True
            continue
        words = seg
        while words and (words[0][1] in _PREFIX_WORDS or _ASSIGN_RE.match(words[0][1])):
            words = words[1:]
        if words:
            name = words[0][1]
            if name in ("cd", "pushd", "popd"):
                # 條件式、管線或背景裡的 cd 不一定生效；popd 不追堆疊
                piped = prev in ("||", "|", "|&", "&") or op in ("|", "|&", "&")
                cur = None if piped or name == "popd" else _cd_target(words[1:], cur)
            elif name.replace("\\", "/").rsplit("/", 1)[-1].lower() in ("git", "git.exe"):
                hit = _git_commit_args(words[1:], cur)
                if hit is not None:
                    found.append((hit[0], hit[1], heredoc, expanding))
        seg, heredoc, skip_next = [], False, False
        if op == "(":
            stack.append(cur)
        elif op == ")":
            cur = stack.pop() if stack else None
        prev = op
    return found


def _commit_message_sources(args):
    """回傳（{種類: [值 word...]}, 有沒有 --amend）；種類是 m／F／C／c／fixup。"""
    src, amend, i = {}, False, 0
    while i < len(args):
        w = args[i]
        t = w[1]
        i += 1
        if t == "--":
            break
        if t.startswith("--"):
            name, eq, val = t.partition("=")
            if name == "--amend":
                amend = True
            elif name in _COMMIT_LONG_ARG:
                if eq:
                    vw = ("w", val, w[2], False)
                elif i < len(args):
                    vw = args[i]
                    i += 1
                else:
                    break
                if _COMMIT_LONG_ARG[name]:
                    src.setdefault(_COMMIT_LONG_ARG[name], []).append(vw)
        elif t.startswith("-") and len(t) > 1:
            for j, ch in enumerate(t[1:], start=2):
                if ch in _COMMIT_SHORT_OPTARG:
                    break
                if ch in _COMMIT_SHORT_ARG:
                    if t[j:]:
                        vw = ("w", t[j:], w[2], False)
                    elif i < len(args):
                        vw = args[i]
                        i += 1
                    else:
                        break
                    if ch != "t":
                        src.setdefault(ch, []).append(vw)
                    break
    return src, amend


def _read_message_file(path):
    try:
        if path.stat().st_size > MAX_MSG_BYTES:
            return None
        data = path.read_bytes()
    except (OSError, ValueError):  # ValueError：路徑含 NUL
        return None
    # 訊息含 NUL（UTF-16、二進位檔）git 會拒絕 commit，當成不知道
    return None if b"\0" in data else data.decode("utf-8", errors="replace")


def _commit_message_state(d, args, heredoc, expanding):
    """回傳 "missing"（確定沒有 Verified:）、"present" 或 None（不知道）。呼叫前已確定指令字串沒有 Verified:。"""
    src, amend = _commit_message_sources(args)
    if "fixup" in src or len(src) > 1:
        return None  # fixup／squash 之後會被壓掉；混用 -m／-F／-C／-c 時 git 本身會拒絕
    if "m" in src:
        # 訊息就寫在指令裡；只有 $(cat file)、$VAR 這種從別處拿的不算
        if any(w[2] and ("<<" not in w[1] or expanding) for w in src["m"]):
            return None
        return "missing"
    if "F" in src:
        w = src["F"][-1]
        if w[1] == "-":  # 從 stdin 讀：只認同一段的 heredoc
            return "missing" if heredoc and not expanding else None
        path = _to_path(w, d)
        text = _read_message_file(path) if path is not None else None
    elif "C" in src or "c" in src or amend:
        # -C／-c／--amend（含 --no-edit）沿用既有 commit 的訊息
        w = (src.get("C") or src.get("c") or [None])[-1]
        if w is not None and (w[2] or w[1].startswith("-") or "\0" in w[1]):
            return None
        rev = w[1] if w is not None else "HEAD"
        text = _git(d, "log", "-1", "--format=%B", rev + "^{commit}", "--")
    else:
        return None  # 沒給訊息會開編輯器，或用 MERGE_MSG、template，內容不知道
    if text is None:
        return None
    return "present" if has_verified_line(text) else "missing"


def unverified_commit_root(command, cwd, skip_roots):
    """指令裡有一個確定沒寫 Verified: 的 git commit 就回它的 repo；其餘（有寫、OSS、判斷不出來）回 None。"""
    try:
        commits = _git_commits(command, cwd)
    except ValueError:
        return None
    for d, args, heredoc, expanding in commits:
        root = repo_root(d) if d is not None else None
        if root is None or any(_under(root, pre) for pre in skip_roots):
            continue  # 找不到 repo 就當不知道；OSS 照上游 commit 慣例
        if _commit_message_state(d, args, heredoc, expanding) == "missing":
            return root
    return None


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

    commit_root = None
    if is_commit:
        commit_root = unverified_commit_root(command, cwd, cfg["skip_commit_roots"])
        is_commit = commit_root is not None
    if is_pr and code_reviewed(scan_transcript(event.get("transcript_path"))):
        is_pr = False

    for flag, check, reason, repo in (
            (is_commit, "commit-without-verified", COMMIT_REASON, commit_root),
            (is_pr, "pr-without-code-review", PR_REASON, root)):
        if not flag:
            continue
        append_log({"event": "pre-bash", "mode": cfg["mode"], "session": sid,
                    "repo": str(repo) if repo else "", "check": check, "would_block": True})
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
