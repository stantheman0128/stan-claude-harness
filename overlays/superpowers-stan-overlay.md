# superpowers — Stan overlay patch 檔（重貼指引）

plugin 升級會建新版本目錄、不會帶走這個 overlay。每次 `claude plugin update superpowers` 後重貼。

目前套用於：6.3.0（2026-09-19）。驗證：`grep -l "Stan overlay" ~/.claude/plugins/cache/superpowers-marketplace/superpowers/<版本>/hooks/hooks.json`。

## 1. `hooks/hooks.json` — 拿掉 SessionStart 注入（2026-09-19，Fable 5.1 稽核）

原因：hook 每次 startup/clear/compact 注入 `using-superpowers` SKILL.md 全文（約 6.2 KB），內容是「1% 機率適用就 ABSOLUTELY MUST 載 skill」這類壓力語言，與全域 CLAUDE.md 第 1 條「skill 是帶脈絡的工具，不是必經流程」直接衝突。skill 本身不受影響：superpowers 各 skill 的 description 仍在 system prompt 的 skill 清單，照常可被 Skill 工具呼叫。

作法：先 `cp hooks.json hooks.json.upstream`，再把 `hooks.json` 改成

```json
{
  "_stan_overlay": "Stan overlay 2026-09-19: SessionStart injection removed ... see ~/.claude/overlays/superpowers-stan-overlay.md",
  "hooks": {}
}
```

還原：`cp hooks.json.upstream hooks.json`。
