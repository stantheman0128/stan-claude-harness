#!/bin/bash
# claude-mem port sync hook
# Runs on SessionStart AFTER worker starts.
# Scans ports to find the actual healthy worker, then updates settings to match.

SETTINGS_FILE="$HOME/.claude-mem/settings.json"
CONFIGURED_PORT=$(grep -o '"CLAUDE_MEM_WORKER_PORT"[[:space:]]*:[[:space:]]*"[0-9]*"' "$SETTINGS_FILE" 2>/dev/null | grep -o '[0-9]*')
CONFIGURED_PORT=${CONFIGURED_PORT:-37777}

# If configured port is healthy, nothing to do
if curl -sf "http://127.0.0.1:${CONFIGURED_PORT}/health" --max-time 1 >/dev/null 2>&1; then
  exit 0
fi

# Configured port is not healthy — scan for the real one
for PORT in $(seq 37777 37800); do
  if curl -sf "http://127.0.0.1:${PORT}/health" --max-time 1 >/dev/null 2>&1; then
    # Found healthy worker — update settings
    sed -i "s/\"CLAUDE_MEM_WORKER_PORT\"[[:space:]]*:[[:space:]]*\"[0-9]*\"/\"CLAUDE_MEM_WORKER_PORT\": \"$PORT\"/" "$SETTINGS_FILE"
    # Also update worker.pid
    echo "{\"port\": $PORT}" > "$HOME/.claude-mem/worker.pid"
    exit 0
  fi
done

# No healthy worker found — nothing we can do
exit 0
