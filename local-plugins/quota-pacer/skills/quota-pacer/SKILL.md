---
name: quota-pacer
description: 額度感知的任務節奏器。Stan 用白話給這個 session 設用量上限時就載入，不用等他打斜線指令：例如「不要用超過 5% 的 weekly」「這次最多用 X%」「weekly 到 60% 就停」「別把額度燒光」「用量省著點、快到就收手」。也用於在有限用量下跑較長任務、要邊做邊看用量、接近限制前主動收手並寫交接。觸發詞：不要用超過、最多用、用量上限、額度上限、到 X% 就停、quota pacer、額度感知、邊做邊看用量、燒到快沒之前收手、pace against quota、5h-override、在 weekly 見底前收手。
---

# Quota Pacer

在有限用量下跑一個大任務：邊做邊印用量、接近綁定限制前主動收手、沒做完就寫交接。用量有兩個來源：桌面 App 的 `get_usage` 工具（優先），和腳本自己打官方 endpoint（備援）。互動 CLI、桌面 App、SDK、headless 都能用。

`SCRIPTS` = `C:/Users/stans/.claude/local-plugins/quota-pacer/scripts`
`ACTIVE` = `C:/Users/stans/.claude/quota-pacer/active.json`

## 用量來源：先 App，後 endpoint

每次要讀用量之前（啟動時，以及工作迴圈每次裁決之前）先做這一步：

1. 如果這個 session 有 `mcp__ccd_session_mgmt__get_usage`（桌面 App 才有；列在 deferred tools 時先用 ToolSearch 載入），呼叫它，不帶參數。它走 App 自己的登入，不會遇到 token 過期。
2. 從回傳的 `plan` 取「已用百分比」和重置時間，交給腳本寫檔。沒有的那條就省略那個參數：
   ```bash
   py "$SCRIPTS/write_usage.py" --five-hour <5h%>@<重置時間> --weekly <weekly%>@<重置時間> --scoped fable=<fable%>@<重置時間>
   ```
   重置時間照工具給的原樣貼（ISO 8601 或 epoch 秒），沒有就只寫百分比。工具給的若是「剩餘」百分比，先換成已用（100 減它）。per-model 的每週限制每條一個 `--scoped 名稱=…`。
3. 工具不存在、被權限擋、或 `plan` 狀態是 unavailable／not_applicable → 跳過這一步，不要停。後面的 `read_usage.py`／`eval_pace.py` 會自己打 endpoint。

寫完之後檔案是新的，後面的腳本直接讀檔，不會再打 endpoint。

## 啟動

Stan 多半不會打 `/quota-pace`，而是在交代任務時順口講一句上限。聽到就照這一節開工，不用請他改用指令。

1. 解析使用者意圖：**任務內容**、**用量上限**（見下表）、是否 `5h-override`（只管 weekly、忽略 5h）、可選的**時間上限**（「30m」「跑 30 分就停」→ `--minutes 30`）。

   | Stan 的說法 | 意思 | 參數 |
   |---|---|---|
   | 「不要用超過 5%」「這次最多用 5%」「只給你 5% 的額度」 | 這個 session 最多再花 5 個百分點 | `--budget 5` |
   | 「weekly 到 60% 就停」「不要讓 weekly 超過 60%」「停在 60%」 | weekly 的絕對水位 | `--cap 60` |
   | 沒講數字，只說「別燒光」「快沒就收手」 | 只防撞到 100% | 不帶 |

   分不出是「再花多少」還是「絕對水位」時：數字不高於現在的 weekly 用量，只可能是前者，用 `--budget`；其餘照字面最接近的那一列選，並在第 3 步的回報裡講明你用了哪種解讀，Stan 一眼就能糾正。
2. 先做上面「用量來源」那一步，再開工：
   ```bash
   py "$SCRIPTS/start_pace.py" [--budget <pp> | --cap <%>] [--minutes <N>] [--mode 5h-override]
   ```
   它讀當前用量記成基準、算好上限、寫 `ACTIVE`，並印出每條限制會在幾 % 收尾、停手、硬擋。
   - `--budget` 同時套在 weekly（全部模型）和每條 per-model weekly（如 fable），各自從自己的起點加，先到的先觸發。
   - `--cap` 只管 weekly（全部模型）。
   - exit 4 = 用量讀不到。把它印的那行原因原樣轉給使用者（例如 token 過期要去 PowerShell 跑一次 CLI）。有給時間上限就改跑純時間盒（只帶 `--minutes`）；沒給就別硬跑，回報使用者。
   - exit 2 = 參數不對（例如 `--cap` 低於現在的用量），照它印的訊息修正或回問。
3. 把 `start_pace.py` 印的那幾行轉給使用者（一兩行就好）：上限是多少、會在幾 % 收手。

`ACTIVE` 的格式（腳本寫的，除錯時才需要看）：
```json
{ "mode": "both", "started": <epoch>, "minutes": <可省>,
  "u0": { "seven_day": 49, "scoped": { "fable": 52 } },
  "ceiling": { "seven_day": 54, "scoped": { "fable": 57 } } }
```
`ceiling` 沒寫的那條上限就是 100。

## 工作迴圈

把任務切成一塊塊做。**每做完一塊**先做「用量來源」那一步更新檔案，再裁決一次：
```bash
py "$SCRIPTS/eval_pace.py" "$ACTIVE"
```
把那一行原樣印給使用者（它就是「邊做邊看進度」），再依 VERDICT 行動：

- **CONTINUE** → 做下一塊。
- **WINDDOWN** → 不要再開新的大塊，把手上這塊收束到一個乾淨的停止點，準備收尾。
- **HARDSTOP** → 停止接新工作，進「收尾」。
- **EMERGENCY** → 已燒穿 buffer（hook 也會開始擋工具），立刻用最少動作結束。

trigger 可能是 `time`、`5h`、`weekly`，或 `weekly[fable]` 這種 per-model 限制。

## 收尾

到 HARDSTOP（或使用者喊停）：

- **任務已完成** → 印一段完成總結（做了什麼、狀態）。
- **任務未完成** → 用剩下的 buffer 產交接：呼叫 `handoff` skill 寫一份 HANDOFF.md，內容涵蓋目前進度、還沒做的 roadmap、如何交接、下個 session 怎麼接手；同時把重點印出來。

收尾完成後刪掉基準檔：
```bash
rm -f "$ACTIVE"
```
（任務正常做完、或中途結束，都要刪，避免殘留 active.json 讓 hook 誤擋下一個 session。）

## 門檻與微調（測試用）

裁決門檻可用環境變數覆寫（eval_pace 會吃）：
`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90) `QP_GRACE_MIN`(3) `QP_NOTICE_MIN`(2) `QP_REFRESH_COOLDOWN_SEC`(60)

刷新紀錄：每次嘗試（含被冷卻擋下的）記一行在 `C:/Users/stans/.claude/quota-pacer/refresh.log`，讀數怪的時候先看最後幾行。

資料源可覆寫：`QP_CRED_FILE`（OAuth credentials 路徑）、`QP_USAGE_URL`、`QP_USAGE_STATE`。

時間盒：`minutes−QP_GRACE_MIN` 強制收手寫交接、`minutes` 整為 hook 硬擋死線。

用量上限：設了 `ceiling` 的那條，收尾、停手、硬擋三條線都改成相對於那個上限算，固定的 pp 值（FLOOR 等）會跟著預算縮小。用量百分比通常是整數，所以很小的預算（1 到 2 個百分點）只分得出「還沒到」和「到了」。

測試時把 `QP_HARD_RATIO` 或門檻調到「現在就會踩到」的位置，即可在不真的燒爆的情況下驗證收手與交接流程。

## 限制

- 單一 session 假設：`active.json` 與 `usage-state.json` 都是全域單檔，兩個並行 pacer session 會互相蓋。
- 互動 CLI 下 statusline 會用「無 scoped」版本蓋 `usage-state.json`；eval_pace 發現 u0 有 scoped 基準但檔案沒資料時會補刷一次（60s 冷卻），所以 scoped 裁決最多延遲一個冷卻窗。
- 靠 skill 自律逐塊 check；hook 只是最後一層 EMERGENCY 硬保險（且不自動刷新，用的是最後一次已知用量），不是每塊的節奏控制。
