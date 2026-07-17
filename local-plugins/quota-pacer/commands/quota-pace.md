---
description: 在額度節奏下跑一個較長任務——邊做邊看用量、接近限制前主動收手並寫交接。用法 /quota-pace [5h-override] <任務>
---

使用者要在「額度感知節奏」下跑一個較長的任務。

任務與選項：$ARGUMENTS

載入 `quota-pacer` skill，照它的協定執行：
- 若 `$ARGUMENTS` 含 `5h-override`，用 5h-override 模式（只看 weekly、忽略 5h），其餘文字為任務內容；否則 both 模式。
- 起點讀用量寫 `active.json` → 分塊做、每塊後跑 `eval_pace.py` 印進度 → WINDDOWN 收手、HARDSTOP 停並收尾（未完成呼叫 `handoff` skill 寫交接）→ 收尾刪 `active.json`。
- 只在互動式 CLI 有效；讀不到用量（MISSING/STALE）先請使用者敲一下刷新，別硬跑。
