# Restore claude-mem (paused 2026-08-25)

Data in `C:\Users\stans\.claude-mem` was **not** deleted.

## Resume

1. Delete `C:\Users\stans\.claude-mem\.paused`
2. In `C:\Users\stans\.claude\settings.json`:
   - Set `"claude-mem@thedotmack": true`
   - Put the hook blocks below back into `hooks.SessionStart` and `hooks.Stop`
3. Restart Claude Code (and Cursor if you want the memory MCP tools again)

## SessionStart hooks to restore (before skill-routing-watch)

```json
{
  "matcher": "startup",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"C:/Users/stans/.claude/hooks/claude-mem-port-sync.sh\"",
      "timeout": 25
    }
  ]
},
{
  "matcher": "startup",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"C:/Users/stans/.claude/hooks/fix-claude-mem-windows.sh\"",
      "timeout": 10
    }
  ]
},
{
  "matcher": "startup",
  "hooks": [
    {
      "type": "command",
      "command": "node \"C:/Users/stans/.claude/hooks/claude-mem-sync.mjs\" download",
      "timeout": 30
    }
  ]
},
{
  "matcher": "startup",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"C:/Users/stans/.claude/hooks/claude-mem-context.sh\"",
      "timeout": 15
    }
  ]
}
```

## Stop hook to restore (after twify-session-name, before skill-usage-log)

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "node \"C:/Users/stans/.claude/hooks/claude-mem-sync.mjs\" upload",
      "timeout": 120
    }
  ]
}
```

Custom hook scripts still exist; they no-op while `.paused` is present.
