"""PreToolUse guard for eval runs: confine writes to the throwaway repo.

The live config pre-approves Write even under dontAsk, so --allowedTools
alone cannot narrow it. run.py passes this hook through --settings; it exits
2 (block) for:
  - Edit/Write/NotebookEdit/MultiEdit outside the repo
  - Bash/PowerShell unless every subcommand starts with an allowed prefix,
    with no output redirection and no command substitution
  - every MCP tool
Usage (from the hook): python -I guard.py <guard.json>
"""
import json
import re
import sys
from pathlib import Path

SPLIT_RE = re.compile(r"&&|\|\||;|\||\n")
REDIRECT_RE = re.compile(r"(?<![0-9&=-])>")  # 2>&1, => and -> are not redirects
SAFE_REDIRECT_RE = re.compile(r"\d?>\s*(/dev/null|&\d)")


def block(msg: str) -> None:
    print(f"harness-eval guard: {msg}", file=sys.stderr)
    sys.exit(2)


def inside(path: str, cwd: str, repo: Path) -> bool:
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd) / p
    p = p.resolve()
    return p == repo or repo in p.parents


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    repo = Path(cfg["repo"]).resolve()
    ev = json.load(sys.stdin)
    tool, inp, cwd = ev.get("tool_name", ""), ev.get("tool_input") or {}, ev.get("cwd") or str(repo)
    if tool.startswith("mcp__"):
        block(f"MCP tool {tool} is not available in this eval")
    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        target = inp.get("file_path") or inp.get("notebook_path") or ""
        if not target or not inside(target, cwd, repo):
            block(f"{tool} outside the eval repo: {target}")
        return
    if tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", ""))
        if "$(" in cmd or "`" in cmd:
            block("command substitution is not allowed")
        if REDIRECT_RE.search(SAFE_REDIRECT_RE.sub("", cmd)):
            block("output redirection is not allowed")
        for part in (s.strip() for s in SPLIT_RE.split(cmd)):
            if part and not any(part == p or part.startswith(p + " ") for p in cfg["allow_prefixes"]):
                block(f"command not on this scenario's list: {part[:80]}")


if __name__ == "__main__":
    main()
