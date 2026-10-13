#!/bin/bash
# Auto-fix claude-mem worker-service.cjs for Windows
# Runs on SessionStart — patches hardcoded macOS paths if detected
# Related: https://github.com/thedotmack/claude-mem/issues/1513

[ -f "$HOME/.claude-mem/.paused" ] && exit 0

FILE="$HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"

[ ! -f "$FILE" ] && exit 0

# Only patch if the known bad pattern exists (idempotent check)
if grep -q '/Users/alexnewman/conductor' "$FILE" 2>/dev/null; then
  # Fix 1: __dirname in init_paths → correct modes/DB resolution
  sed -i 's|var __dirname = "/Users/alexnewman/conductor/workspaces/claude-mem/banjul/src/shared"|var __dirname = dirname2(fileURLToPath(import.meta.url))|' "$FILE"

  # Fix 2: __filename in worker-service section → correct daemon spawn
  sed -i 's|__filename = "/Users/alexnewman/conductor/workspaces/claude-mem/banjul/src/services/worker-service.ts"|__filename = fileURLToPath(import.meta.url)|' "$FILE"

  # Clear stale state so worker can restart fresh
  rm -f "$HOME/.claude-mem/.worker-start-attempted"
  [ -f "$HOME/.claude-mem/supervisor.json" ] && echo '{"processes":{}}' > "$HOME/.claude-mem/supervisor.json"
fi

# Fix 3: isMainModule .cjs check (separate pattern — survives even if paths change)
if grep -q 'endsWith("worker-service");' "$FILE" 2>/dev/null && ! grep -q 'endsWith("worker-service.cjs")' "$FILE" 2>/dev/null; then
  sed -i 's|\.endsWith("worker-service");|.endsWith("worker-service") || process.argv[1]?.endsWith("worker-service.cjs");|' "$FILE"
fi

exit 0
