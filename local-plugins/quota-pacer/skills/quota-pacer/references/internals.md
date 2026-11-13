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

## 三條線怎麼算

對每條限制：`avail = 上限 − 起點`，`rem = 上限 − 現在`。

- 收尾（WINDDOWN）：`rem ≤ max(10% × avail, 停手線 + GAP)`
- 停手（HARDSTOP）：`rem ≤ max(5% × avail, FLOOR)`
- 硬擋（EMERGENCY）：`rem ≤ EMERGENCY`

上限是 100 時 `FLOOR`=3、`GAP`=1、`EMERGENCY`=1 個百分點。上限是自訂預算時，這三個值各自縮成不超過 `avail` 的 20%、20%、10%，不然 5 個百分點的預算會被 3 個百分點的 `FLOOR` 吃掉大半。

時間盒：第 `minutes − 3 − 2` 分收尾，第 `minutes − 3` 分停手，第 `minutes` 分硬擋。

## hook（`hooks/hardstop_guard.py`）

每次工具呼叫前跑。只在 EMERGENCY 擋，停手那層刻意不擋，留給寫交接。它只讀檔、不去拉用量，所以用的是最後一次寫進檔的數字；檔案超過 90 秒沒更新就只看時間盒。放行的情況：`active.json` 的 `session` 不是這個 session、開工超過 24 小時、指令是 pacer 自己的腳本、工具是 `get_usage` 或 `ToolSearch`。

## 環境變數

門檻：`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_NOTICE_GAP_PP`(1) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90) `QP_GRACE_MIN`(3) `QP_NOTICE_MIN`(2) `QP_REFRESH_COOLDOWN_SEC`(60) `QP_ACTIVE_MAX_HOURS`(24)

路徑：`QP_ACTIVE_FILE` `QP_USAGE_STATE` `QP_CRED_FILE` `QP_USAGE_URL` `QP_REFRESH_LOG`

測試時把路徑全指到暫存資料夾、用 `write_usage.py` 餵假讀數，就能在不動到真實設定的情況下驗證收手流程。

## 已知限制

- 互動 CLI 下 statusline 會用沒有 per-model 資料的版本蓋掉 `usage-state.json`。`eval_pace.py` 發現開工時有 per-model 基準、檔案裡卻沒有時會補拉一次（60 秒冷卻），拉不到就在行尾印 `⚠`。
- 每段之間的檢查靠 agent 自律，hook 只是最後一層。
