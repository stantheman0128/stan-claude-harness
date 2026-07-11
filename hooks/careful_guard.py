"""Careful mode guard — blocks dangerous commands when .careful-mode flag exists."""
import json
import sys
import re
import os

FLAG_FILE = os.path.expanduser("~/.claude/.careful-mode")

# If careful mode is not active, allow everything
if not os.path.exists(FLAG_FILE):
    sys.exit(0)

input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")

# Only check Bash commands
if tool_name != "Bash":
    sys.exit(0)

command = input_data.get("tool_input", {}).get("command", "")

# Dangerous patterns to block in careful mode
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
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": f"CAREFUL MODE: '{name}' blocked. Disable with /careful-off or manually dismiss."
            }
        }
        print(json.dumps(output))
        sys.exit(0)

sys.exit(0)
