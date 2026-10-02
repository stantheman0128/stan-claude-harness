# 資料來源與時效

引用任何數字前先看這份，確認資料沒過期、不在未驗證項裡。

## 來源

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點」。資料來源為 2026-09-23 官方 docs（models overview、choosing-a-model、effort、fast-mode、Opus 5.5 what's-new / prompting 指南、Claude Code model-config / changelog）與 Opus 5.5 發佈文，逐條有據。Opus 5.5 System Card（230 頁，2026-09-22）已讀 §1.5、§3.2–3.4、§5.2、§6 與 §8，摘要在下方「System Card 摘要」節，每條附頁碼。2026-09-30 補 Sonnet 5.5：官方 docs（overview、what's-new、migration、prompting、effort）、Claude Code model-config / settings-reference / changelog、發佈文與 System Card（148 頁）。2026-10-02 加「升階路徑」與禁用 Haiku（Stan 決定）。

（上段是 2026-10-03 拆檔前 SKILL.md 的 Overview 原文；「下方 System Card 摘要」現在是 `opus55-system-card.md`。）

## 資料時效

2026-09-23 調研（Opus 5.5 發佈次日），同日補讀 System Card §1.5/§3/§5/§6。2026-09-26 補讀 Thariq effort 文與 CC prompt-caching 文件：確認 Opus 5.5 / Fable 5.1 中途換 effort 保 cache、fast mode 只有第一次開會重讀。未驗證項：Max 方案 Opus 5.5 額度桶歸屬、桌面 app Code 分頁的貼上是否走同一套 `[Pasted text #N]` 標記（文件只寫 CLI 終端）。2026-09-30 補 Sonnet 5.5（發佈後兩天），並更正設定鍵名為 `modelSettings[...].effortLevel`。Sonnet 5.5 未驗證項：Bedrock 可用性（overview 有列、what's-new 沒列）、各檔位在 HLE/OSWorld 的成本（System Card 只有圖）。Haiku 5.5 發佈後，先查 platform.claude.com/docs 的 models overview 與 effort 頁再回答，數字過期就別引用。2026-10-02 加升階路徑：訊號與梯子由本檔既有官方數據和 Thariq 文推導，停損次數與「非安全題 Opus @ high 在主 session 做」是自訂規則；同日依 Stan 決定禁用 Haiku，agent 定義改成 scout→sonnet、verifier→high。

2026-10-03：新增 `executor-high` agent（Opus 5.5 @ high），補上升階路徑裡「非安全題 Opus @ high」的角色，上一段那條自訂規則因此作廢。同日把 SKILL.md 拆成本體加 `references/` 五個檔，內容逐行核對沒有遺漏。
