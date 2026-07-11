#!/bin/bash
# claude-mem context hook (with retry)
# Waits for worker to be healthy, then fetches CMEM context block.
# Returns hookSpecificOutput.additionalContext for system prompt injection.

SETTINGS_FILE="$HOME/.claude-mem/settings.json"
PORT=$(grep -o '"CLAUDE_MEM_WORKER_PORT"[[:space:]]*:[[:space:]]*"[0-9]*"' "$SETTINGS_FILE" 2>/dev/null | grep -o '[0-9]*')
PORT=${PORT:-37777}
HOST="127.0.0.1"

# Wait up to 8 seconds for worker to be healthy
for i in 1 2 3 4 5 6 7 8; do
  if curl -sf "http://$HOST:$PORT/health" --max-time 1 >/dev/null 2>&1; then
    # Worker is healthy — run context hook
    _R="${CLAUDE_PLUGIN_ROOT}"
    [ -z "$_R" ] && _R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
    node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" hook claude-code context 2>/dev/null
    exit 0
  fi
  sleep 1
done

# Worker never became healthy — return empty (no CMEM block, but don't block session)
echo '{}'
exit 0
