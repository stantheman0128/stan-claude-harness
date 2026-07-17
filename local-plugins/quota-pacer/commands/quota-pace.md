---
description: 在額度或時間節奏下跑一個較長任務——邊做邊看用量/時間、接近限制前主動收手並寫交接。用法 /quota-pace [5h-override] [<N>m] <任務>
---

使用者要在「額度感知 / 時間盒節奏」下跑一個較長的任務。

任務與選項：$ARGUMENTS

載入 `quota-pacer` skill，照它的協定執行：
- 解析 `$ARGUMENTS`：`5h-override`（只看 weekly、忽略 5h）、`<N>m`（時間上限，例如 `30m`）、其餘文字為任務內容。至少要有用量基準或時間上限其一。
- 起點寫 `active.json`（`u0` 和/或 `minutes`、`started`）→ 分塊做、每塊後跑 `eval_pace.py` 印進度 → WINDDOWN 收手、HARDSTOP 停並收尾（未完成呼叫 `handoff` skill 寫交接）→ 收尾刪 `active.json`。
- 時間盒只靠牆鐘、哪裡都能用；純用量模式讀不到用量（MISSING/STALE）先請使用者敲一下刷新，別硬跑。
