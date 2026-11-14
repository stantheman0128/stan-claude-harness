---
name: careful
description: Use when the user says "/careful", "careful mode", "小心模式", "啟用保護", or when about to work on production systems, critical data, or irreversible operations. Activates a guard that blocks dangerous commands (rm -rf, force push, DROP TABLE, etc.) for the rest of the session.
---

# Careful Mode（小心模式）

啟用後，PreToolUse hook 會阻擋以下危險指令直到 session 結束或手動關閉：

- `rm -rf` / `git push --force` / `git reset --hard`
- `DROP TABLE` / `DROP DATABASE` / `TRUNCATE`
- `DELETE FROM ... WHERE` (mass delete)
- `kubectl delete` / `dd` / `mkfs`
- `git branch -D` / `git clean -f` / `git checkout --`

## 啟用

建立 flag 檔案即可啟用：

```bash
touch ~/.claude/.careful-mode
```

啟用後回覆使用者：「Careful mode 已啟用。危險指令（rm -rf, force push, DROP TABLE 等）將被自動阻擋。」

## 關閉

使用者說 "/careful-off" 或 "關閉小心模式" 時：

```bash
rm ~/.claude/.careful-mode
```

## 機制

Hook script 位於 `~/.claude/hooks/mode_guard.py`（2026-11-14 與 research mode 的 guard 合併成一支，直接用 `C:/Python313/python.exe -I` 呼叫），註冊為 PreToolUse hook，每次 Bash、Edit、Write、NotebookEdit 呼叫時檢查 flag 檔案是否存在，不存在就直接放行。舊的 `careful_guard.py` 留著備查，已不在 settings.json 裡。
