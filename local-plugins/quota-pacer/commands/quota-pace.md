---
description: 在額度或時間節奏下跑一個較長任務——邊做邊看用量/時間、接近限制前主動收手並寫交接。用法 /quota-pace [budget=<pp>|cap=<%>] [5h-override] [<N>m] <任務>
---

使用者要在「額度感知 / 時間盒節奏」下跑一個較長的任務。

任務與選項：$ARGUMENTS

載入 `quota-pacer` skill，照它的協定執行：
- 解析 `$ARGUMENTS`：`budget=5`（這次最多再用 5 個百分點）或 `cap=60`（weekly 到 60% 就停）、`5h-override`（只看 weekly、忽略 5h）、`<N>m`（時間上限，例如 `30m`）、其餘文字為任務內容。至少要有用量基準或時間上限其一。
- 起點跑 `start_pace.py` 寫 `active.json`（基準、上限、時間盒）→ 分塊做、每塊後跑 `eval_pace.py` 印進度 → WINDDOWN 收手、HARDSTOP 停並收尾（未完成呼叫 `handoff` skill 寫交接）→ 收尾跑 `end_pace.py` 關掉 pacer。
- 用量自動從官方 endpoint 拉（STALE 自刷新），任何 harness 都能用；自刷新失敗時 `read_usage.py` 第一行會印 `UNUSABLE 原因 → 處置`（token 過期、網路、冷卻分開報），把那行轉給使用者；沒給時間上限就停下回報。
