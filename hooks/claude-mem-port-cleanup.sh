#!/bin/bash
# claude-mem port cleanup hook
# Runs on SessionStart BEFORE worker starts.
# If the configured port is held by a dead/ghost process, try to free it.
# If the ghost socket can't be cleared, auto-increment port in settings.json.

SETTINGS_FILE="$HOME/.claude-mem/settings.json"
PORT=$(grep -o '"CLAUDE_MEM_WORKER_PORT"[[:space:]]*:[[:space:]]*"[0-9]*"' "$SETTINGS_FILE" 2>/dev/null | grep -o '[0-9]*')
PORT=${PORT:-37778}

# Check if port is in use
OWNER=$(powershell -NoProfile -Command "
  \$c = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
  if (\$c) { \$c.OwningProcess } else { '' }
" 2>/dev/null | tr -d '[:space:]')

[ -z "$OWNER" ] && exit 0

# Port is in use — check if the worker is healthy
if curl -sf "http://127.0.0.1:$PORT/health" --max-time 2 >/dev/null 2>&1; then
  exit 0
fi

# Port is bound but worker is not responding — zombie or ghost
# Try to kill the owning process
taskkill //PID "$OWNER" //T //F >/dev/null 2>&1
sleep 2

# Check if port was freed
STILL_HELD=$(powershell -NoProfile -Command "
  \$c = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
  if (\$c) { 'yes' } else { '' }
" 2>/dev/null | tr -d '[:space:]')

if [ -n "$STILL_HELD" ]; then
  # Ghost socket — can't be freed without reboot. Auto-increment port.
  NEW_PORT=$((PORT + 1))
  sed -i "s/\"CLAUDE_MEM_WORKER_PORT\"[[:space:]]*:[[:space:]]*\"[0-9]*\"/\"CLAUDE_MEM_WORKER_PORT\": \"$NEW_PORT\"/" "$SETTINGS_FILE"
fi

# Clean up lock files
rm -f "$HOME/.claude-mem/.worker-start-attempted"
[ -f "$HOME/.claude-mem/supervisor.json" ] && echo '{"processes":{}}' > "$HOME/.claude-mem/supervisor.json"

exit 0
