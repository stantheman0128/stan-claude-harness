---
name: quota-pacer
description: 額度感知的任務節奏器。當 Stan 要在有限的用量下跑一個較長的任務、希望它邊做邊看用量、接近限制前主動收手並寫交接時使用。觸發詞：quota pacer、額度感知、邊做邊看用量、燒到快沒之前收手、pace against quota、5h-override、在 weekly 見底前收手。只在互動式 CLI 有效。
---

# Quota Pacer

在有限用量下跑一個大任務：邊做邊印用量、接近綁定限制前主動收手、沒做完就寫交接。**只在互動式 CLI 有效**，因為只有那裡的 statusline 會餵新鮮的官方用量到 `~/.claude/usage-state.json`。

`SCRIPTS` = `C:/Users/stans/.claude/local-plugins/quota-pacer/scripts`
`ACTIVE` = `C:/Users/stans/.claude/quota-pacer/active.json`

## 啟動

1. 解析使用者意圖：**任務內容**、是否 `5h-override`（只管 weekly、忽略 5h）、以及可選的**時間上限**（例如「30m」「跑 30 分就停」→ minutes=30）。
2. 讀當前用量當基準：
   ```bash
   py "$SCRIPTS/read_usage.py" --json
   ```
   - 讀得到 → 記下 u0。
   - 讀不到（MISSING/STALE/null）：**若有給時間上限** → 走純時間盒，跳過 u0 照樣開工（時間 guard 只靠牆鐘）；**若沒給時間上限** → 這是純用量模式卻讀不到，先請使用者敲一下 Enter 讓 statusline 重繪再讀，還是不行就別硬跑。
3. 寫基準檔 `ACTIVE`（目錄不存在先建）。至少要有 `u0` 或 `minutes` 其一，否則沒有任何 guard：
   ```json
   { "mode": "both", "u0": { "five_hour": <5h%>, "seven_day": <weekly%> }, "started": <epoch>, "minutes": <時間上限或省略> }
   ```
   `5h-override` 時 `mode` 改 `"5h-override"`；純時間盒可省略 `u0`/`mode`。
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

## 收尾

到 HARDSTOP（或使用者喊停）：

- **任務已完成** → 在 CLI 印一段完成總結（做了什麼、狀態）。
- **任務未完成** → 用剩下的 buffer 產交接：呼叫 `handoff` skill 寫一份 HANDOFF.md，內容涵蓋目前進度、還沒做的 roadmap、如何交接、下個 session 怎麼接手；同時把重點印在 CLI。

收尾完成後刪掉基準檔：
```bash
rm -f "$ACTIVE"
```
（任務正常做完、或中途結束，都要刪，避免殘留 active.json 讓 hook 誤擋下一個 session。）

## 門檻與微調（測試用）

裁決門檻可用環境變數覆寫（eval_pace 會吃）：
`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90) `QP_GRACE_MIN`(3) `QP_NOTICE_MIN`(2)

時間盒：`minutes−QP_GRACE_MIN` 強制收手寫交接、`minutes` 整為 hook 硬擋死線。

測試時把 `QP_HARD_RATIO` 或門檻調到「現在就會踩到」的位置，即可在不真的燒爆的情況下驗證收手與交接流程。

## 限制（v1）

- **用量 guard** 只在互動式 CLI 有效（SDK/背景/App 讀不到新鮮用量）；**時間 guard 靠牆鐘，哪裡都能用**。
- 單一 session 假設：`active.json` 與 `usage-state.json` 都是全域單檔，兩個並行 pacer session 會互相蓋。
- per-model（Fable）weekly 目前機器讀不到，不納入 guard。
- 靠 skill 自律逐塊 check；hook 只是最後一層 EMERGENCY 硬保險，不是每塊的節奏控制。
