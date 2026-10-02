# Changelog

## 0.1.0 (2026-10-03)

- 新增 `agent.spawn` hook：Agent 工具明確帶含 `haiku` 的 model 時回 `{ deny }`，subagent 不啟動，Claude 收到改派指示。fork 不擋（fork 忽略 model 參數）。
- 沒帶 model、由 agent 定義 pin 到 haiku 的派工照常啟動，只在 transcript 記一行提醒。
- 已知限制：hook 出錯時 Claude Code 會略過它、照常啟動 subagent（fail-open）。型別依據是 Claude Code 2.1.277 產生的 `mods/types/claude-code.d.ts`，目標版本 v2.1.287。
- `hooks/register.js` 第一次寫入被 auto mode 以「自我修改」擋下，Stan 在對話中核可後建立。
- 2026-10-03 Stan 在 CC 2.1.287 實跑：`claude plugin validate` 通過（`hooks: agent.spawn`、`calls: $.ui.log`），`claude plugin test` 3 pass 0 fail，已用 user scope 安裝。
- 尚未驗證：新 session 裡實際派一次帶 haiku 的 subagent。
