"""PreToolUse guard for eval runs: keep the model inside the throwaway repo.

run.py registers this hook for every tool through --settings. It denies by
default and exits 2 (block), also when the event's cwd is not inside the
repo and when the guard itself fails (Claude Code treats exit 1 as a
non-blocking error and runs the tool). Otherwise the call must be one of:
  - a tool in READ_TOOLS (reading, searching, skills, subagents)
  - Edit/Write/NotebookEdit/MultiEdit on an absolute path inside the repo,
    not inside or named .git, .claude or .mcp.json
  - Bash whose command splits into simple commands joined only by |, ||,
    &&, ; or newlines, each starting with one of the scenario's
    allow_prefixes. Any other shell syntax is blocked: $ expansion,
    backticks, ( ), { }, a lone &, <( ), >( ), here-docs, an unquoted #
    starting a word (a comment), every < and every > except N>&M and
    N>/dev/null. cd and every command not in
    READ_ONLY_CMDS must keep path arguments inside the repo, and git may not
    get options that write a file or run a program.
PowerShell is blocked because no scenario needs it.
Usage (from the hook): python -I guard.py <guard.json>
"""
import json
import os
import re
import sys
from pathlib import Path

READ_TOOLS = {"Read", "Glob", "Grep", "Agent", "Task", "Skill", "ToolSearch", "TodoWrite",
              "TaskCreate", "TaskGet", "TaskList", "TaskUpdate"}
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
# Only read; their arguments may name any path.
READ_ONLY_CMDS = {"cat", "head", "tail", "grep", "wc", "ls", "pwd"}
# git long options that write a file, run a program or change config. Any
# prefix is blocked as well, since git accepts unambiguous abbreviations.
GIT_BAD_OPTS = ("output", "ext-diff", "textconv", "exec", "config")
GIT_OK_EXACT = {"text"}  # real option that is also a prefix of textconv
# .claude and .mcp.json: Claude Code reloads project skills during a session
# and a skill's !`cmd` lines run without this hook.
OFF_LIMITS = {".git", ".claude", ".mcp.json"}
SEPARATORS = {"|", "||", "&&", ";"}
REDIRECTS = {">", ">>", "&>", "&>>", ">&"}
OP_CHARS = "|&;<>()"
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class Blocked(Exception):
    pass


def block(msg: str) -> None:
    try:
        print(f"harness-eval guard: {msg}", file=sys.stderr)
    finally:
        sys.exit(2)


def inside(p: Path, repo: Path) -> bool:
    return p == repo or repo in p.parents


def edit_problem(target, repo: Path) -> str:
    if not isinstance(target, str) or not target:
        return "no file path"
    if CONTROL_RE.search(target) or "\n" in target or re.search(r"[$%]", target):
        return f"unusual characters in path: {target!r}"
    p = Path(target)
    if not p.is_absolute():
        return f"not an absolute path: {target}"
    try:
        p = p.resolve()
    except (OSError, ValueError, RuntimeError):
        return f"cannot resolve: {target}"
    if not inside(p, repo):
        return f"outside the eval repo: {target}"
    for part in p.parts[len(repo.parts):]:
        name = part.rstrip(" .").casefold()
        if ":" in part or name in OFF_LIMITS or re.fullmatch(r"git~\d+", name):
            return f"{part} is off limits: {target}"
    return ""


def tokenize(cmd: str) -> list:
    """Split a bash command into ("w", text, flags) and ("op", text) tokens.

    Understands quotes, backslashes and operators; raises Blocked on
    everything else bash would expand. flags marks unquoted globs (* ? [)
    and a ~ that bash may expand.
    """
    toks, buf, flags = [], [], set()
    in_word = quoted = False
    i, n = 0, len(cmd)

    def end():
        nonlocal buf, flags, in_word, quoted
        if in_word:
            toks.append(("w", "".join(buf), frozenset(flags)))
        buf, flags, in_word, quoted = [], set(), False, False

    while i < n:
        c = cmd[i]
        if c == "\\":
            if i + 1 >= n:
                raise Blocked("trailing backslash")
            if cmd[i + 1] != "\n":  # backslash-newline joins lines
                buf.append(cmd[i + 1])
                in_word = quoted = True
            i += 2
        elif c == "'":
            j = cmd.find("'", i + 1)
            if j < 0:
                raise Blocked("unterminated quote")
            buf.append(cmd[i + 1:j])
            in_word = quoted = True
            i = j + 1
        elif c == '"':
            in_word = quoted = True
            i += 1
            while True:
                if i >= n:
                    raise Blocked("unterminated quote")
                d = cmd[i]
                if d == '"':
                    i += 1
                    break
                if d in "$`":
                    raise Blocked("$ and backticks are not allowed")
                if d == "\\" and i + 1 < n and cmd[i + 1] in '$`"\\\n':
                    if cmd[i + 1] != "\n":
                        buf.append(cmd[i + 1])
                    i += 2
                    continue
                buf.append(d)
                i += 1
        elif c in "$`":
            raise Blocked("$ and backticks are not allowed")
        elif c in "{}":
            raise Blocked("braces are not allowed")
        elif c in " \t":
            end()
            i += 1
        elif c == "\n":
            end()
            toks.append(("op", ";"))
            i += 1
        elif c in OP_CHARS:
            j = i
            while j < n and cmd[j] in OP_CHARS:
                j += 1
            op = cmd[i:j]
            if op[0] in "<>" and in_word and not quoted and re.fullmatch(r"[0-9]+", "".join(buf)):
                buf, in_word = [], False  # file descriptor number, as in 2>
            end()
            toks.append(("op", op))
            i = j
        elif c == "#" and not in_word:
            raise Blocked("an unquoted # starting a word is a bash comment; not allowed")
        else:
            if c in "*?[":
                flags.add("glob")
            elif c == "~" and (not in_word or "".join(buf)[-1:] in ("=", ":")):
                flags.add("tilde")
            buf.append(c)
            in_word = True
            i += 1
    end()
    return toks


def split_commands(toks: list) -> list:
    """Group tokens into simple commands, dropping allowed redirections."""
    cmds, cur, i = [], [], 0
    while i < len(toks):
        t = toks[i]
        if t[0] == "w":
            cur.append(t)
            i += 1
            continue
        op = t[1]
        if op in SEPARATORS:
            if cur:
                cmds.append(cur)
            cur = []
            i += 1
            continue
        if op not in REDIRECTS:
            raise Blocked(f"shell syntax {op!r} is not allowed")
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        target = nxt[1] if nxt and nxt[0] == "w" and not nxt[2] else None
        if not ((op == ">&" and target and re.fullmatch(r"[0-9]+", target))
                or (op != ">&" and target == "/dev/null")):
            raise Blocked(f"redirection {op} {target or ''} is not allowed; only N>&M and N>/dev/null")
        i += 2
    if cur:
        cmds.append(cur)
    return cmds


def shell_path(word: str, base):
    """The path Git Bash would use for word, or None when it cannot be told.

    With base None, only an absolute word resolves."""
    w = word
    if os.name == "nt":
        m = re.match(r"/([A-Za-z])(?=/|$)", w)
        if m:
            w = m.group(1) + ":" + (w[2:] or "/")
        elif w.startswith(("/", "\\")):
            return None  # MSYS mount such as /tmp, or a UNC path
    try:
        p = Path(w)
        if not p.is_absolute():
            if base is None:
                return None
            p = base / p
        return p.resolve()
    except (OSError, ValueError, RuntimeError):
        return None


def path_values(word: str) -> list:
    vals = [word]
    if word.startswith("-") and "=" in word:
        vals.append(word.split("=", 1)[1])
    if re.match(r"-[^-]", word) and len(word) > 2:
        vals.append(word[2:])
    return vals


def check_command(words: list, prefixes: list, repo: Path, cwds: set) -> set:
    """Validate one simple command; return the set of possible cwds after it."""
    argv = [w[1] for w in words]
    match = next((p.split() for p in prefixes if argv[:len(p.split())] == p.split()), None)
    if match is None:
        raise Blocked(f"command not on this scenario's list: {' '.join(argv)[:80]}")
    args = words[len(match):]
    if argv[0] in READ_ONLY_CMDS:
        return cwds

    def all_inside(value):
        return all((p := shell_path(value, b)) is not None and inside(p, repo) for b in cwds)

    if argv[0] == "cd":
        if len(args) != 1 or args[0][1].startswith("-") or args[0][2]:
            raise Blocked("cd takes exactly one plain directory")
        if not all_inside(args[0][1]):
            raise Blocked(f"cd outside the eval repo: {args[0][1][:80]}")
        # cd can fail (then the cwd stays), so keep both possibilities.
        return cwds | {shell_path(args[0][1], b) for b in cwds}
    for text, flags in ((w[1], w[2]) for w in args):
        if flags:
            raise Blocked(f"unquoted glob or ~ is not allowed here: {text[:60]}")
        if argv[0] == "git" and text.startswith("--"):
            opt = text[2:].split("=", 1)[0]
            if opt and opt not in GIT_OK_EXACT and any(b.startswith(opt) for b in GIT_BAD_OPTS):
                raise Blocked(f"git option {text[:60]} can write files or run programs")
        if not all(all_inside(v) for v in path_values(text)):
            raise Blocked(f"path outside the eval repo: {text[:80]}")
    return cwds


def check_bash(cmd: str, prefixes: list, repo: Path, cwd: Path) -> None:
    if CONTROL_RE.search(cmd):
        raise Blocked("control character in command")
    cwds = {repo, cwd}
    for words in split_commands(tokenize(cmd)):
        cwds = check_command(words, prefixes, repo, cwds)


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    repo = Path(cfg["repo"]).resolve()
    ev = json.load(sys.stdin)
    tool, inp = ev.get("tool_name", ""), ev.get("tool_input") or {}
    raw_cwd = ev.get("cwd")
    cwd = shell_path(raw_cwd, None) if isinstance(raw_cwd, str) else None
    if cwd is None or not inside(cwd, repo):
        block(f"session cwd is not inside the eval repo: {raw_cwd!r}")
    if tool in ("Agent", "Task") and inp.get("isolation"):
        block("subagents with isolation are not available in this eval")
    if tool in READ_TOOLS:
        return
    if tool in EDIT_TOOLS:
        problem = edit_problem(inp.get("file_path") or inp.get("notebook_path"), repo)
        if problem:
            block(f"{tool} blocked: {problem}")
        return
    if tool == "Bash":
        try:
            check_bash(str(inp.get("command", "")), cfg["allow_prefixes"], repo, cwd)
        except Blocked as e:
            block(str(e))
        return
    block(f"tool {tool} is not available in this eval")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 - fail closed: exit 1 would let the tool run
        block(f"guard error, blocking: {type(e).__name__}: {e}")
