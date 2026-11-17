"""Careful + research mode guard (PreToolUse). Merges careful_guard.py and research_guard.py into one process.

careful mode (~/.claude/.careful-mode): blocks dangerous Bash commands.
research mode (~/.claude/.research-mode): blocks Edit/Write/NotebookEdit and file-writing Bash commands.
With neither flag present it exits at once without reading stdin, same as the two old scripts.
"""
import os
import sys

HOME = os.path.expanduser("~/.claude")
careful = os.path.exists(os.path.join(HOME, ".careful-mode"))
research = os.path.exists(os.path.join(HOME, ".research-mode"))
if not (careful or research):
    sys.exit(0)

import json
import re

# Decode as UTF-8 explicitly: -I ignores PYTHONUTF8, and the console code page (cp950) would corrupt CJK commands.
data = json.loads(sys.stdin.buffer.read().decode("utf-8", "surrogateescape"))
tool = data.get("tool_name", "")
command = data.get("tool_input", {}).get("command", "") if tool == "Bash" else ""


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": reason}}))
    sys.exit(0)


if research:
    if tool in {"Edit", "Write", "NotebookEdit"}:
        deny(f"RESEARCH MODE: {tool} blocked. Only read/search operations allowed. Disable with /research-off.")
    if tool == "Bash" and any(p in command for p in (">", ">>", "tee ", "mv ", "cp ", "mkdir ", "touch ")):
        deny("RESEARCH MODE: File-writing bash command blocked. Only read operations allowed. Disable with /research-off.")

if careful and tool == "Bash":
    DANGEROUS_PATTERNS = [
        (r"\brm\s+-rf\b", "rm -rf"),
        (r"\bgit\s+push\s+--force\b", "git push --force"),
        (r"\bgit\s+push\s+-f\b", "git push -f"),
        (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
        (r"\bgit\s+checkout\s+--\s", "git checkout --"),
        (r"\bgit\s+checkout\s+\.", "git checkout . (整個工作目錄丟棄)"),
        (r"\bgit\s+restore\s+\.", "git restore . (整個工作目錄丟棄)"),
        (r"\bDROP\s+TABLE\b", "DROP TABLE"),
        (r"\bDROP\s+DATABASE\b", "DROP DATABASE"),
        (r"\bTRUNCATE\b", "TRUNCATE"),
        (r"\bDELETE\s+FROM\b.*\bWHERE\b.*=.*", "DELETE FROM (mass delete)"),
        (r"\bkubectl\s+delete\b", "kubectl delete"),
        (r"\bdd\s+if=", "dd"),
        (r"\bmkfs\b", "mkfs"),
        (r"\bgit\s+branch\s+-D\b", "git branch -D"),
        (r"\bgit\s+clean\s+-f", "git clean -f"),
    ]
    for pattern, name in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            deny(f"CAREFUL MODE: '{name}' blocked. Disable with /careful-off or manually dismiss.")

sys.exit(0)
