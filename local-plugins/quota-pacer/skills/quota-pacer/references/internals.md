# Quota Pacer 內部細節

除錯或測試時才需要。平常照 SKILL.md 做就夠。

## 檔案

- `C:/Users/stans/.claude/quota-pacer/sessions/<session 編號>.json`：開工設定，一個 session 一個檔，`start_pace.py` 寫、`end_pace.py` 刪（只刪自己的）。腳本從環境變數 `CLAUDE_CODE_SESSION_ID` 知道自己是哪個 session，跟 hook 收到的 `session_id` 是同一個值。
- `C:/Users/stans/.claude/quota-pacer/active.json`：舊的共用檔。只有腳本不知道自己是哪個 session 時（手動在終端機跑）才會寫它。有寫 `session` 的只管那個 session，沒寫的管所有 session。下面的格式兩種檔都一樣。
  ```json
  { "mode": "both", "started": 1794551688, "session": "<session id>", "minutes": 30,
    "u0": { "seven_day": 49, "scoped": { "fable": 52 } },
    "ceiling": { "seven_day": 54, "scoped": { "fable": 57 } } }
  ```
  `u0` 是開工時的用量。`ceiling` 沒寫的那條上限就是 100。`session` 來自環境變數；環境變數沒有時，才用 hook 在看到 `start_pace.py` 時記在 `.starting-session` 的值。
- `C:/Users/stans/.claude/usage-state.json`：最後一次讀到的用量，`write_usage.py` 寫的（`source` 是 `app`）。
- 腳本自己去官方 endpoint 拉用量的功能預設關閉（0.8.0，Stan 定案只用 `get_usage`）。它要用 `.credentials.json` 的 token，那個只有 CLI 會更新。沒有 `get_usage` 的純 CLI 環境要用，設環境變數 `QP_SELF_PULL=1`，這時拉的結果記在 `quota-pacer/refresh.log`，`source` 是 `oauth`。

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
- `C:/Users/stans/.claude/quota-pacer/wrap/`：`wrap-<session>` 記這個 session 在到線後用了幾次工具，`nag-<session>` 記上次提醒補讀數的時間，`lock-<session>` 是單一 session 到線後的鎖（內容是到線的原因）。鎖有兩個來源：hook 在 `EMERGENCY` 擋下工具時、`end_pace.py` 在 `HARDSTOP` 以上收工時。有鎖就擋這個 session 的所有工具（pacer 腳本、`get_usage`、ToolSearch 除外），`QP_LOCK_HOURS`（12）後失效，Stan 親口豁免時 `bypass_prompt.py` 會把鎖刪掉。

## 重置怎麼認

週用量平常只升不降。兩個訊號擇一就當成已重置：

- 現在的用量比看過的最高點低 `QP_RESET_DROP_PP`（3）個百分點以上。
- 開工時記下的重置時刻已經過了 `QP_RESET_LATE_SEC`（3600 秒）。多等一小時是因為 `get_usage` 給的「17 小時後」只準到小時。起點很低、看不出掉的時候靠這條。

只看週限額，5 小時限額重置不算。單一 session 的 pacer 看到重置回 `HARDSTOP reset`，全機規則看到重置就到線。

## 全機規則的生命週期

- 到線：截止時刻到、任一條週限額的裁決到 HARDSTOP、或重置。
- 到線後每個 session 第一次工具呼叫被擋（附說明），接著可以收尾，之後全擋：
  - 因為用量到線：放行到 EMERGENCY 線，也就是上限前 `QP_EMERGENCY_PP`（1）個百分點，上限 100 時是 99%。讀數超過 `QP_GLOBAL_STALE_SEC` 沒更新就退回數次數，不憑舊數字一直放行。
  - 因為時間到或重置：放行 `QP_WRAP_CALLS`（10）次。subagent 的工具呼叫算在同一個 session 的額度裡。
- 失效：到線後 `QP_GLOBAL_HOLD_HOURS`（3）小時，從截止時刻和到線時刻較晚的那個起算；一直沒到線的規則最多活 `QP_GLOBAL_MAX_HOURS`（48）小時。
- 用量超過 `QP_GLOBAL_STALE_SEC`（300）沒更新，hook 擋一次請 session 用 `get_usage` 補讀數，同一 session `QP_NAG_GAP_SEC`（600）內只擋一次。hook 是獨立的程式，自己叫不到 `get_usage`。

## 豁免（`hooks/bypass_prompt.py`，UserPromptSubmit）

只有使用者送出的訊息會觸發它，所以拿它當「Stan 本人說的」的憑據。訊息裡有豁免的說法、而且現在有規則或 pacer 生效，就寫 `wrap/bypass-<session>`，`QP_BYPASS_HOURS`（12）內工具 hook 對那個 session 兩層都不擋。

- 算數的說法：動詞（bypass、豁免、繞過、解除、取消、無視、忽略、不用管、不管）跟對象（用量、額度、weekly、quota、pacer、全機規則、停手）相隔 12 個字以內；或 bypass、豁免、繞過、無視、不管緊接「限制」「上限」；或整則訊息不到 14 個字、裡面有 bypass 或豁免。
- 不算的：說法前 8 個字內有否定詞（不要、別、不准…）；訊息是背景任務通知、subagent 交回、斜線指令展開；`<pasted_content>` 區塊裡的字（整則都是貼上的內容時例外）。
- 排程任務送出的訊息跟 Stan 親手打的分不出來。排程的 prompt 裡不要寫豁免的說法。

工具 hook 另外擋三件事（被豁免的 session 不擋）：有規則時 `global_pace.py --clear`；到線後 `global_pace.py` 的任何設定；有規則或 pacer 生效時，Bash、PowerShell、Write、Edit 的輸入裡出現 `quota-pacer/global.json`、`quota-pacer/active.json`、`quota-pacer/wrap`。最後這項只擋得住直接寫出路徑的做法。

## 三條線怎麼算

對每條限制：`avail = 上限 − 起點`，`rem = 上限 − 現在`。

- 收尾（WINDDOWN）：`rem ≤ max(10% × avail, 停手線 + GAP)`
- 停手（HARDSTOP）：`rem ≤ max(5% × avail, FLOOR)`
- 硬擋（EMERGENCY）：`rem ≤ EMERGENCY`

上限是 100 時 `FLOOR`=3、`GAP`=1、`EMERGENCY`=1 個百分點。上限是自訂預算時，這三個值各自縮成不超過 `avail` 的 20%、20%、10%，不然 5 個百分點的預算會被 3 個百分點的 `FLOOR` 吃掉大半。

時間盒：第 `minutes − 3 − 2` 分收尾，第 `minutes − 3` 分停手，第 `minutes` 分硬擋。

## hook（`hooks/hardstop_guard.py`）

每次工具呼叫前跑，先看全機規則，再看單一 session 的 pacer。下面講的是後者：只在 EMERGENCY 擋，停手那層刻意不擋，留給寫交接。這一層只讀檔、不去拉用量，所以用的是最後一次寫進檔的數字；檔案超過 90 秒沒更新就只看時間盒。它讀這個 session 自己的檔，加上舊共用檔。hook 收不到 session 編號時從嚴，把每個 session 的檔都算進來。放行的情況：設定檔的 `session` 不是這個 session、開工超過 24 小時、指令是 pacer 自己的腳本、工具是 `get_usage` 或 `ToolSearch`。「pacer 自己的腳本」指整行全是這種呼叫：`py "<scripts 資料夾>/<腳本>.py" 參數`，可以用 `&&` 或 `;` 串好幾個，段尾可以有 `>/dev/null`。混進任何別的指令、換行、子指令、或別的資料夾的同名檔，整行都不算。

## 環境變數

門檻：`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_NOTICE_GAP_PP`(1) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90) `QP_GRACE_MIN`(3) `QP_NOTICE_MIN`(2) `QP_REFRESH_COOLDOWN_SEC`(60) `QP_ACTIVE_MAX_HOURS`(24)

路徑：`QP_ACTIVE_FILE` `QP_USAGE_STATE` `QP_CRED_FILE` `QP_USAGE_URL` `QP_REFRESH_LOG`

測試時把路徑全指到暫存資料夾、用 `write_usage.py` 餵假讀數，就能在不動到真實設定的情況下驗證收手流程。

## 已知限制

- 互動 CLI 下 statusline 會用沒有 per-model 資料的版本蓋掉 `usage-state.json`。`eval_pace.py` 發現開工時有 per-model 基準、檔案裡卻沒有時會補拉一次（60 秒冷卻），拉不到就在行尾印 `⚠`。
- 單一 session 的 pacer，每段之間的檢查靠 agent 自律，hook 只是最後一層。全機規則不靠自律。
- hook 是 session 開啟時載入的。plugin 裝上之前就開著的 session 不受全機規則管，要重開。
- 被全機規則擋下的 session 如果掛著會自動叫它繼續的機制（Stop hook 之類），會一直被叫起來又被擋，白燒用量。
- session 跟 Stan 是同一個 Windows 帳號，規則檔、鎖檔、這個 plugin 的程式它都碰得到。這套東西擋的是「不知道有上限」和「順手就想繼續」的 session，擋不住故意變花樣的：換個寫法叫腳本讓 hook 認不出來、寫程式去刪檔、拿掉環境變數假裝是終端機、自己跑 `bypass_prompt.py`、寫假讀數。三輪獨立複驗（11-23）每輪都找得到新寫法，Stan 定案不再往這個方向補。
- 解除或放寬全機規則的檢查在 `global_pace.py` 自己裡面（`guard`）：腳本知道自己是哪個 session 叫的，那個 session 沒被豁免就拒絕。hook 那一層還留著，但 hook 只認得標準寫法。
- 豁免的說法靠關鍵字比對，會有誤判。偏向寧可不放行：沒被認出來時 session 會請 Stan 講「豁免」兩個字。
- 有規則生效時，session 想看 `refresh.log` 以外的狀態檔會被擋，改用 `global_pace.py --status`。
