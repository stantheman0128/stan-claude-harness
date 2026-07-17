---
name: quota-pacer
description: 額度感知的任務節奏器。當 Stan 要在有限的用量下跑一個較長的任務、希望它邊做邊看用量、接近限制前主動收手並寫交接時使用。觸發詞：quota pacer、額度感知、邊做邊看用量、燒到快沒之前收手、pace against quota、5h-override、在 weekly 見底前收手。只在互動式 CLI 有效。
---

# Quota Pacer

在有限用量下跑一個大任務：邊做邊印用量、接近綁定限制前主動收手、沒做完就寫交接。**只在互動式 CLI 有效**，因為只有那裡的 statusline 會餵新鮮的官方用量到 `~/.claude/usage-state.json`。

`SCRIPTS` = `C:/Users/stans/.claude/local-plugins/quota-pacer/scripts`
`ACTIVE` = `C:/Users/stans/.claude/quota-pacer/active.json`

## 啟動

1. 解析使用者意圖：**任務內容**，以及是否 `5h-override`（只管 weekly，忽略 5 小時限制）。
2. 讀當前用量當基準：
   ```bash
   py "$SCRIPTS/read_usage.py" --json
   ```
   若回 MISSING、stale=true、或任一要管的限制 pct 是 null（該次沒帶到那條用量），先請使用者在 CLI 敲一下 Enter 讓 statusline 重繪再讀一次。**讀不到有效基準就不要硬跑。**
3. 寫基準檔 `ACTIVE`（目錄不存在先建）：
   ```json
   { "mode": "both", "u0": { "five_hour": <當前5h%>, "seven_day": <當前weekly%> }, "started": <epoch> }
   ```
   `5h-override` 時 `mode` 改成 `"5h-override"`。
4. 告訴使用者：基準已記、mode、以及會在哪個大概用量收手。

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
`QP_SOFT_RATIO`(0.10) `QP_HARD_RATIO`(0.05) `QP_FLOOR_PP`(3) `QP_EMERGENCY_PP`(1) `QP_STALE_SEC`(90)

測試時把 `QP_HARD_RATIO` 或門檻調到「現在就會踩到」的位置，即可在不真的燒爆的情況下驗證收手與交接流程。

## 限制（v1）

- 只在互動式 CLI；SDK / 背景 session 讀不到新鮮用量。
- 單一 session 假設：`active.json` 與 `usage-state.json` 都是全域單檔，兩個並行 pacer session 會互相蓋。
- per-model（Fable）weekly 目前機器讀不到，不納入 guard。
- 靠 skill 自律逐塊 check；hook 只是最後一層 EMERGENCY 硬保險，不是每塊的節奏控制。
