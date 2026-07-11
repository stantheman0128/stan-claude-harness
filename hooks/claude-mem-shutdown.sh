#!/bin/bash
# claude-mem worker shutdown hook
# Runs on SessionEnd — gracefully shuts down the worker daemon
# so it doesn't linger as a ghost process and leave orphaned TCP sockets.

SETTINGS_FILE="$HOME/.claude-mem/settings.json"
PORT=$(grep -o '"CLAUDE_MEM_WORKER_PORT"[[:space:]]*:[[:space:]]*"[0-9]*"' "$SETTINGS_FILE" 2>/dev/null | grep -o '[0-9]*')
PORT=${PORT:-37778}

# Step 1: Try graceful HTTP shutdown
curl -sf -X POST "http://127.0.0.1:$PORT/api/admin/shutdown" --max-time 3 >/dev/null 2>&1

# Step 2: Wait briefly for port to free
for i in 1 2 3 4 5; do
  sleep 1
  # Check if port is still in use via PowerShell
  OWNER=$(powershell -NoProfile -Command "
    \$c = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
    if (\$c) { \$c.OwningProcess } else { '' }
  " 2>/dev/null | tr -d '[:space:]')
  [ -z "$OWNER" ] && exit 0
done

# Step 3: If still alive, force kill the process tree
if [ -n "$OWNER" ]; then
  taskkill //PID "$OWNER" //T //F >/dev/null 2>&1
fi

# Step 4: Clean up lock files so next session starts fresh
rm -f "$HOME/.claude-mem/.worker-start-attempted"
[ -f "$HOME/.claude-mem/supervisor.json" ] && echo '{"processes":{}}' > "$HOME/.claude-mem/supervisor.json"

exit 0
