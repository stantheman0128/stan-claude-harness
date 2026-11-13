---
name: quota-pacer
description: 額度感知的任務節奏器。當 Stan 要在有限的用量下跑一個較長的任務、希望它邊做邊看用量、接近限制前主動收手並寫交接時使用。觸發詞：quota pacer、額度感知、邊做邊看用量、燒到快沒之前收手、pace against quota、5h-override、在 weekly 見底前收手。
---

# Quota Pacer

在有限用量下跑一個大任務：邊做邊印用量、接近綁定限制前主動收手、沒做完就寫交接。用量自己從官方 endpoint 拉（讀本機 OAuth credentials），**任何 harness 都能用**——互動 CLI、桌面 App、SDK、headless 皆可。

`SCRIPTS` = `C:/Users/stans/.claude/local-plugins/quota-pacer/scripts`
`ACTIVE` = `C:/Users/stans/.claude/quota-pacer/active.json`

## 啟動

1. 解析使用者意圖：**任務內容**、是否 `5h-override`（只管 weekly、忽略 5h）、以及可選的**時間上限**（例如「30m」「跑 30 分就停」→ minutes=30）。
2. 讀當前用量當基準（檔案過舊會自動拉新，不必再叫使用者去 CLI 敲 Enter）：
   ```bash
   py "$SCRIPTS/read_usage.py" --json
   ```
   - `usable` 是 true → 記下 u0（含 `scoped`，per-model weekly 如 fable）。某一條是 null（例如 endpoint 沒回 5h）就不要寫進 u0，那條不設 guard。
   - `usable` 是 false（exit 4 或 3）：這份讀數不能記成 u0。把 `advice` 那一行原樣轉給使用者（它寫了原因和處置，例如 token 過期要去 PowerShell 跑一次 CLI）。接著：**若有給時間上限** → 走純時間盒照樣開工；**若沒給** → 純用量模式沒資料，別硬跑，回報使用者。
3. 寫基準檔 `ACTIVE`（目錄不存在先建）。至少要有 `u0` 或 `minutes` 其一，否則沒有任何 guard：
   ```json
   { "mode": "both",
     "u0": { "five_hour": <5h%>, "seven_day": <weekly%>, "scoped": { "fable": <fable%> } },
     "started": <epoch>, "minutes": <時間上限或省略> }
   ```
   `scoped` 直接抄 read_usage --json 的 `scoped`（沒有就省略）。`5h-override` 時 `mode` 改 `"5h-override"`（scoped 仍然管——它本質是 weekly）；純時間盒可省略 `u0`/`mode`。
4. 告訴使用者：記了什麼（u0 和/或 time-box 幾分）、會在大概什麼用量或第幾分鐘收手。

## 工作迴圈

把任務切成一塊塊做。**每做完一塊**就裁決一次：
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

測試時把 `QP_HARD_RATIO` 或門檻調到「現在就會踩到」的位置，即可在不真的燒爆的情況下驗證收手與交接流程。

## 限制（v0.3）

- 單一 session 假設：`active.json` 與 `usage-state.json` 都是全域單檔，兩個並行 pacer session 會互相蓋。
- 互動 CLI 下 statusline 會用「無 scoped」版本蓋 `usage-state.json`；eval_pace 發現 u0 有 scoped 基準但檔案沒資料時會補刷一次（60s 冷卻），所以 scoped 裁決最多延遲一個冷卻窗。
- 靠 skill 自律逐塊 check；hook 只是最後一層 EMERGENCY 硬保險（且不自動刷新，用的是最後一次已知用量），不是每塊的節奏控制。
