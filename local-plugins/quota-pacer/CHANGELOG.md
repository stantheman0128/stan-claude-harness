# Quota Pacer CHANGELOG

## 0.1.0 — 2026-07-18
初版。額度感知任務節奏器：邊做邊看用量、接近限制前主動收手並寫交接。只在互動式 CLI 有效。

- 門檻模型：每條限制 session 起點記 U0，available=100−U0，wind-down 剩餘≤10%×avail、hard-stop 剩餘≤max(5%×avail, FLOOR=3pp)、EMERGENCY 剩餘≤1pp。5h + weekly 先到者觸發。
- `5h-override` 模式：忽略 5h、只管 weekly。
- 三層：skill 逐塊裁決（收手 / 停+寫交接，未完成呼叫 handoff skill）；PreToolUse hook 只在 EMERGENCY 擋（刻意不擋 hard-stop，保護寫交接的 buffer）；`active.json` 當啟用旗標。
- 資料源：statusline.sh 正式輸出 `~/.claude/usage-state.json`（扶正原本的 debug dump 副作用）。
- 元件：pace_core.py / read_usage.py / eval_pace.py / hooks/hardstop_guard.py / skills/quota-pacer / commands/quota-pace（`/quota-pace` 斜線指令）。
- 驗證：Python 單元 + hook 四情境全綠；fresh verifier 獨立複驗 CONFIRMED；Stan 互動式 CLI 實測兩輪通過（both→HARDSTOP 5h、5h-override→HARDSTOP weekly、收手+交接+清理全對）。

## Roadmap
- 同一 session 靠消耗速率預測，無縫接下一個 5h 窗續跑（免重開 session、免跨 session handoff）。
- 全自動精準 pause N 分鐘再自醒。
- per-model（Fable）weekly guard（待機器可讀 JSON 提供該欄位）。
- FLOOR 實際 pp 值校準；null-pct（statusline 沒帶 rate_limits）是否改為保守處理。
