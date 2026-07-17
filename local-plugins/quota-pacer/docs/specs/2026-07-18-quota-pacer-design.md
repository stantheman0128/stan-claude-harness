# Quota Pacer 設計規格 v1

日期：2026-07-18
狀態：定版，待實作
放置：`C:\Users\stans\.claude\local-plugins\quota-pacer\`（local-plugin，與 loop-gate / burn-credits 並排）

## 目的

給 Quota Pacer 一個大任務，它邊做邊在 CLI 印用量進度，在綁定的用量限制快見底前主動收手、寫收尾，絕不讓使用者被平台硬切。只在互動式 CLI 運作，因為只有那裡的 statusline 才餵得到官方即時用量。

## 範圍

v1（現在做）：
- 包住單一任務，分塊執行。
- 每塊後讀官方用量，印一行進度。
- 對 5h 與 weekly 兩條限制做正規化門檻管控，先到者觸發。
- 5h-override 模式：本次忽略 5h 限制，只管 weekly。
- 到 wind-down 停開新工作、收手；到 hard-stop 強制停，用保留 buffer 寫收尾。
- 收尾：做完印完成總結；沒做完呼叫既有 handoff skill 產交接。
- PreToolUse 硬保險：過 hard-stop 直接擋新工具呼叫，防 agent 恍神燒爆。

roadmap（寫下但不做）：
- 同一 session 靠消耗速率預測，無縫接下一個 5h 窗續跑，免重開 session、免跨 session 交接。
- 全自動精準 pause N 分鐘再自醒。
- per-model（Fable）weekly 管控。目前機器可讀 JSON 不含此欄位。

## 門檻模型

每條啟用中的限制 g，在 session 起點各記一次基準：
- `U0_g` = 起點用量百分比
- `avail_g = 100 − U0_g`（本次可用額度，正規化成 100%）
- `rem_g = 100 − 當下用量`（剩餘百分點）

兩個門檻（百分點）：
- `hard_stop_rem_g = max(0.05 × avail_g, FLOOR)`
- `wind_down_rem_g = max(0.10 × avail_g, hard_stop_rem_g + NOTICE_GAP)`

觸發（任一啟用限制先到者）：
- `rem_g ≤ wind_down_rem_g` → 進入收手：不開新工作、把手上做完、朝停止點走
- `rem_g ≤ hard_stop_rem_g` → 強制停，進收尾寫作
- `rem_g ≤ EMERGENCY`（絕對 pp，預設 1）→ hook 擋下一切工具呼叫，最後一層保險。刻意低於 hard-stop，才不會把寫交接的 buffer 一起擋掉。

用 Stan 的例子（U0=20，avail=80，FLOOR=3）：
- `hard_stop_rem = max(4, 3) = 4pp` → 用到 96% 強制停
- `wind_down_rem = max(8, 5) = 8pp` → 用到 92% 開始收手

符合「剩 10% 注意、剩 5% 強制」。

參數預設（皆可調）：
- 軟門檻比例 0.10、硬門檻比例 0.05
- `FLOOR = 3`（pp）最低保留給收尾的百分點
- `NOTICE_GAP = 1`（pp）確保收手嚴格早於強制停
- `EMERGENCY = 1`（pp）hook 最後保險層，低於 hard-stop
- `STALE = 90`（秒）

## FLOOR 怎麼定

buffer 要蓋住兩件事：兩次檢查間的過衝（每個工具呼叫前用 hook 檢查，過衝至多一次工具呼叫，很小）加上寫 handoff 的成本（呼叫 handoff skill 約一個中等回合）。

問題是用量只量得到百分比、量不到絕對 token，所以無法先驗算「N 個百分點等於幾個 token」。weekly 在 Max 20x 很大，幾個 pp 綽綽有餘；地板真正的作用是在 session 一開機就已經很滿、avail 很小時，把強制停點往前拉、保住收尾空間。

因此預設 `FLOOR = 3pp`，設成可調，實作驗證時實測一次「寫一份 handoff 花掉幾 pp」再校準。這是 v1 唯一需要經驗校準的旋鈕。

## Guards 與 5h-override

啟用限制集合預設 = {5h, weekly}。
5h-override 模式 → 集合 = {weekly}，完全不把 5h 當觸發條件，含 hook 硬保險也跳過 5h。

誠實註記：override 只是「本工具不再對 5h 自我節制」。若真把 5h 用到 100%，平台仍會硬切，這不是本工具能擋的。使用時機正是判斷這個短間隔內衝不破 5h、不值得為它管控。

## 收尾行為

wind-down：停止開新的工作塊，把手上這塊做完，引導 agent 收束到乾淨停止點。

hard-stop：停止接新工作。在保留的 buffer 內：
- 任務完成 → CLI 印完成總結。
- 任務未完成 → 呼叫既有 handoff skill 產 HANDOFF.md（目前進度、未做 roadmap、如何交接、下個 session 怎麼接），同時印在 CLI。

## 元件

1. `scripts/pace_core.py`
   共用核心：讀 usage-state、讀 active.json、算門檻與裁決（CONTINUE / WINDDOWN / HARDSTOP / EMERGENCY，先到者）。hook 與 eval CLI 都 import 它。

2. `scripts/read_usage.py`
   印當前 5h%、weekly%、resets 倒數、age、STALE。`--json` 供 skill 記基準。

3. `scripts/eval_pace.py`
   skill 每做完一塊叫它：吃 active.json + usage-state，印 `<VERDICT> <trigger> | 進度`。門檻可由環境變數覆寫（測試用）。

4. `statusline.sh` 補一行（改現有檔）
   除現有 debug dump 外，明確寫 `~/.claude/usage-state.json`：`{five_hour:{pct,resets_at}, seven_day:{pct,resets_at}, ts}`。把資料源從脆弱的 debug 副作用扶正。

5. `hooks/hardstop_guard.py`（PreToolUse）
   最後一層硬保險。active.json 不存在（pacer 未啟用）→ 放行。啟用且任一啟用限制達 EMERGENCY（rem ≤ 1pp）→ 擋工具呼叫（exit 2）。刻意不擋在 hard-stop，否則會連寫交接的 Write 一起擋掉。讀不到 / STALE → fail-open 放行。跳過 override 掉的限制。

6. `skills/quota-pacer/SKILL.md`
   指揮：起點記基準到 `~/.claude/quota-pacer/active.json` → 分塊跑任務 → 每塊後叫 read_usage + eval_pace → 印進度列 → 依裁決行動（繼續 / 收手 / 強制停加收尾，未完成呼叫 handoff skill）。收尾後刪 active.json。吃參數：任務描述、mode（5h-override）、門檻覆寫。

7. `commands/quota-pace.md`（斜線指令）
   `/quota-pace [5h-override] <任務>`：薄包裝，載入 quota-pacer skill 並照協定跑。協定單一來源在 SKILL.md，指令不重複邏輯。

## 資料流

- TUI 重繪 → `statusline.sh` 寫 `usage-state.json`
- skill 啟動 → 寫 `active.json`（mode、U0 基準）
- 每塊工作後 → `read_usage.sh` + `eval_pace.sh` → 印進度加裁決
- 每個工具呼叫前 → `hardstop_guard.py` 讀 usage-state 加 session config → 過硬門檻則擋

## 錯誤與邊界

- usage-state 缺失或 STALE（>90s）：讀取器回報，skill 印警告並退保守（提早收手），或請使用者先敲一下觸發 statusline 重繪。
- 讀不到 weekly 欄位：只用讀得到的限制當 guard。
- session 起點某限制已過 hard-stop（avail 極小）：pacer 拒絕開重活、直接警告，或立即寫交接。
- avail 小到 wind_down_rem ≥ avail：起點即在收手區，警告。

## 設定（環境變數）

`QP_SOFT_RATIO=0.10` `QP_HARD_RATIO=0.05` `QP_FLOOR_PP=3` `QP_NOTICE_GAP_PP=1` `QP_EMERGENCY_PP=1` `QP_STALE_SEC=90`
mode：預設 both；`5h-override` 切 weekly-only。

## 測試與驗證

- `read_usage.sh` 冒煙：直接跑，應印當前用量；STALE 時敲一下 CLI 再跑。
- 強制觸發：用門檻覆寫把 hard-stop 設到略高於當前用量，給一個 trivial 長任務，看是否印進度加收手加寫交接。
- override：開 5h-override，確認 5h 不再觸發。
- hook 保險：把用量狀態偽造成過硬門檻，確認新工具呼叫被擋。
- 派 fresh verifier subagent 獨立複驗，讀加跑、不改。

## 未決 / 校準

- FLOOR 實際 pp 值：實測一份 handoff 的實耗後校準。
