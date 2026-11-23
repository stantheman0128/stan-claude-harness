# Quota Pacer 內部細節

除錯或測試時才需要。平常照 SKILL.md 做就夠。

## 檔案

- `C:/Users/stans/.claude/quota-pacer/active.json`：開工設定，`start_pace.py` 寫、`end_pace.py` 刪。
  ```json
  { "mode": "both", "started": 1794551688, "session": "<session id>", "minutes": 30,
    "u0": { "seven_day": 49, "scoped": { "fable": 52 } },
    "ceiling": { "seven_day": 54, "scoped": { "fable": 57 } } }
  ```
  `u0` 是開工時的用量。`ceiling` 沒寫的那條上限就是 100。`session` 由 hook 在看到 `start_pace.py` 時先記在 `.starting-session`，再由 `start_pace.py` 抄進來。
- `C:/Users/stans/.claude/usage-state.json`：最後一次讀到的用量。`source` 是 `app`（`write_usage.py` 寫的）或 `oauth`（腳本自己拉的）。
- `C:/Users/stans/.claude/quota-pacer/refresh.log`：每次去 endpoint 拉用量的結果，一行一筆 JSON。

- `C:/Users/stans/.claude/quota-pacer/global.json`：全機規則，`global_pace.py` 寫。
  ```json
  { "set": 1794551688, "until": 1794574800,
    "u0": { "seven_day": 49, "scoped": { "fable": 52 } },
    "resets": { "seven_day": 1794700000 },
    "ceiling": { "seven_day": 80 },
    "peak": { "seven_day": 61 },
    "stopped": { "reason": "time", "text": "已到截止時間 11-24 05:00", "t": 1794574801 } }
  ```
  `peak` 是看過的最高用量，`stopped` 一寫下去就維持到規則失效。`active.json` 也有 `resets`、`peak`，重置後多一個 `reset`。
- `C:/Users/stans/.claude/quota-pacer/wrap/`：`wrap-<session>` 記這個 session 在到線後用了幾次工具，`nag-<session>` 記上次提醒補讀數的時間。

## 重置怎麼認

週用量平常只升不降。兩個訊號擇一就當成已重置：

- 現在的用量比看過的最高點低 `QP_RESET_DROP_PP`（3）個百分點以上。
- 開工時記下的重置時刻已經過了 `QP_RESET_LATE_SEC`（3600 秒）。多等一小時是因為 `get_usage` 給的「17 小時後」只準到小時。起點很低、看不出掉的時候靠這條。

只看週限額，5 小時限額重置不算。單一 session 的 pacer 看到重置回 `HARDSTOP reset`，全機規則看到重置就到線。

## 全機規則的生命週期

- 到線：截止時刻到、任一條週限額的裁決到 HARDSTOP、或重置。
- 到線後每個 session 第一次工具呼叫被擋（附說明），接著放行 `QP_WRAP_CALLS`（10）次，之後全擋。subagent 的工具呼叫算在同一個 session 的額度裡。
- 失效：到線後 `QP_GLOBAL_HOLD_HOURS`（3）小時，從截止時刻和到線時刻較晚的那個起算；一直沒到線的規則最多活 `QP_GLOBAL_MAX_HOURS`（48）小時。
- 用量超過 `QP_GLOBAL_STALE_SEC`（300）沒更新，hook 會自己去 endpoint 拉（4 秒逾時，60 秒冷卻）。拉不到就擋一次請 session 補讀數，同一 session `QP_NAG_GAP_SEC`（600）內只擋一次。

## 三條線怎麼算

對每條限制：`avail = 上限 − 起點`，`rem = 上限 − 現在`。

- 收尾（WINDDOWN）：`rem ≤ max(10% × avail, 停手線 + GAP)`
- 停手（HARDSTOP）：`rem ≤ max(5% × avail, FLOOR)`
- 硬擋（EMERGENCY）：`rem ≤ EMERGENCY`

上限是 100 時 `FLOOR`=3、`GAP`=1、`EMERGENCY`=1 個百分點。上限是自訂預算時，這三個值各自縮成不超過 `avail` 的 20%、20%、10%，不然 5 個百分點的預算會被 3 個百分點的 `FLOOR` 吃掉大半。

時間盒：第 `minutes − 3 − 2` 分收尾，第 `minutes − 3` 分停手，第 `minutes` 分硬擋。

## hook（`hooks/hardstop_guard.py`）

每次工具呼叫前跑，先看全機規則，再看單一 session 的 pacer。下面講的是後者：只在 EMERGENCY 擋，停手那層刻意不擋，留給寫交接。這一層只讀檔、不去拉用量，所以用的是最後一次寫進檔的數字；檔案超過 90 秒沒更新就只看時間盒。放行的情況：`active.json` 的 `session` 不是這個 session、開工超過 24 小時、指令是 pacer 自己的腳本、工具是 `get_usage` 或 `ToolSearch`。「pacer 自己的腳本」指整行剛好是一次呼叫（`py "<scripts 資料夾>/<腳本>.py" 參數`），後面接別的指令、換行、或別的資料夾的同名檔都不算，所以 SKILL 裡的指令要一行一個、照完整路徑寫。

## 環境變數

門檻：`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_NOTICE_GAP_PP`(1) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90) `QP_GRACE_MIN`(3) `QP_NOTICE_MIN`(2) `QP_REFRESH_COOLDOWN_SEC`(60) `QP_ACTIVE_MAX_HOURS`(24)

路徑：`QP_ACTIVE_FILE` `QP_USAGE_STATE` `QP_CRED_FILE` `QP_USAGE_URL` `QP_REFRESH_LOG`

測試時把路徑全指到暫存資料夾、用 `write_usage.py` 餵假讀數，就能在不動到真實設定的情況下驗證收手流程。

## 已知限制

- 互動 CLI 下 statusline 會用沒有 per-model 資料的版本蓋掉 `usage-state.json`。`eval_pace.py` 發現開工時有 per-model 基準、檔案裡卻沒有時會補拉一次（60 秒冷卻），拉不到就在行尾印 `⚠`。
- 單一 session 的 pacer，每段之間的檢查靠 agent 自律，hook 只是最後一層。全機規則不靠自律。
- hook 是 session 開啟時載入的。plugin 裝上之前就開著的 session 不受全機規則管，要重開。
- 被全機規則擋下的 session 如果掛著會自動叫它繼續的機制（Stop hook 之類），會一直被叫起來又被擋，白燒用量。
- 全機規則擋不住 session 自己跑 `global_pace.py --clear`，只靠訊息裡的交代。
