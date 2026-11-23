# 資料來源與時效

引用任何數字前先看這份，確認資料沒過期、不在未驗證項裡。

## 來源

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點」。資料來源為 2026-09-23 官方 docs（models overview、choosing-a-model、effort、fast-mode、Opus 5.5 what's-new / prompting 指南、Claude Code model-config / changelog）與 Opus 5.5 發佈文，逐條有據。Opus 5.5 System Card（230 頁，2026-09-22）已讀 §1.5、§3.2–3.4、§5.2、§6 與 §8，摘要在下方「System Card 摘要」節，每條附頁碼。2026-09-30 補 Sonnet 5.5：官方 docs（overview、what's-new、migration、prompting、effort）、Claude Code model-config / settings-reference / changelog、發佈文與 System Card（148 頁）。2026-10-02 加「升階路徑」與禁用 Haiku（Stan 決定）。2026-10-13 Stan 解禁 Haiku 5.5，同日查證規格並改成品質優先版（見資料時效最後一段）。

（上段是 2026-10-03 拆檔前 SKILL.md 的 Overview 原文；「下方 System Card 摘要」現在是 `opus55-system-card.md`。）

## 資料時效

2026-09-23 調研（Opus 5.5 發佈次日），同日補讀 System Card §1.5/§3/§5/§6。2026-09-26 補讀 Thariq effort 文與 CC prompt-caching 文件：確認 Opus 5.5 / Fable 5.1 中途換 effort 保 cache、fast mode 只有第一次開會重讀。未驗證項：Max 方案 Opus 5.5 額度桶歸屬、桌面 app Code 分頁的貼上是否走同一套 `[Pasted text #N]` 標記（文件只寫 CLI 終端）。2026-09-30 補 Sonnet 5.5（發佈後兩天），並更正設定鍵名為 `modelSettings[...].effortLevel`。Sonnet 5.5 未驗證項：Bedrock 可用性（overview 有列、what's-new 沒列）、各檔位在 HLE/OSWorld 的成本（System Card 只有圖）。Haiku 5.5 發佈後，先查 platform.claude.com/docs 的 models overview 與 effort 頁再回答，數字過期就別引用。2026-10-02 加升階路徑：訊號與梯子由本檔既有官方數據和 Thariq 文推導，停損次數與「非安全題 Opus @ high 在主 session 做」是自訂規則；同日依 Stan 決定禁用 Haiku，agent 定義改成 scout→sonnet、verifier→high。

2026-10-03：新增 `executor-high` agent（Opus 5.5 @ high），補上升階路徑裡「非安全題 Opus @ high」的角色，上一段那條自訂規則因此作廢。同日把 SKILL.md 拆成本體加 `references/` 五個檔；連結全部指得到檔案，破折號沒有新增，舊版逐行比對還沒跑（本機 CPU 滿載排隊中）。

2026-10-13：品質優先版（Stan 定案「整版採用」）。來源是 `Projects\model-blackbox-eval\research-2026-10-13\` 四份研究筆記（official.md：四份 System Card 與發佈文；api-guidance.md：platform.claude.com 的 effort、choosing-a-model、optimizing-for-cost-and-intelligence、各模型 prompting 指南；claude-code.md：code.claude.com 的 model-config、sub-agents、settings、changelog 2.1.221 到 2.1.296；independent.md：CursorBench 4.0、Artificial Analysis、Vals、Endor Labs、METR），整理稿是同專案 `ROUTING-2026-10-13.md`（§0.1 為定案版）。這次改的：起點全面升一格（主 session 與 executor Opus high；executor-high、security-executor Opus xhigh；scout、mech-executor Sonnet high；fan-out sonnet + xhigh、haiku + high）；Haiku 5.5 規格查證完；Sonnet 5.5 cache read 改 $0.10；Agent 工具 v2.1.292 起能帶 effort；更正「`/effort high` 後按 `s`」的錯誤說法；補 Stan 的 settings 現況；Fable 加上弱點修補的例外；卡關後的 max 與 Fable 改成回報 Stan 決定。未驗證項：subagent 沒帶 effort 時是否繼承 session（文件只暗示）；Anthropic 沒用文字公布 Sonnet 5.5、Haiku 5.5 的逐檔分數；沒有 Haiku 或 Sonnet 5.5 當 Opus 下屬 worker 的實測（官方 orchestrator 實驗用 Sonnet 5 當 worker，結論是主模型自己降 effort 單跑每次都贏）；Endor Labs 只有一份且 effort 沒標。

2026-10-18：Stan 要求對照 Artificial Analysis 的細項。x.com 沒登入看不到內容，改從 artificialanalysis.ai 二十個變體頁（`/models/claude-opus-5-5-high` 這種網址）抽頁面內嵌的原始數據，總分與每題成本跟 10-13 的表一致，新增的是逐項拆分（表在 `effort-evidence.md`）。Stan 核可後改了四點：fan-out 用 Sonnet xhigh 的理由改成分散額度（AA 上 Opus high 更便宜也更高分）；Opus max 加上「要求準確的知識型長交付物」這個用途，coding 卡關那條註明證據偏弱；Sonnet max 從禁用改成 Opus xhigh 卡關後終端機任務的候選；Fable 補 AA 的反證。AA-Briefcase 分數 AA 有重算（high 1688、xhigh 1766、max 1805）。未驗證項：AA 分數的信賴區間（頁面沒給，1 到 2 分的差距不一定顯著）；Sonnet FrontierCode xhigh 52.1 的出處沒重查，AA 只測 max。

2026-11-14：Fable 5.2 研究（Fable 5.2 與 Mythos 5.2 2026-11-09 發佈）。讀了 Fable 5.2 / Mythos 5.2 System Card 全文（264 頁，https://assets.claude.com/27d60918d218125e7504bc7354c4b4626ec56b11.pdf）、platform.claude.com 的 models overview、fable-5-2 overview、whats-new-fable-5-2、migration-guide、effort、effort-per-message、choosing-a-model、pricing、preserved-thinking、advisor-tool、prompting-claude-fable-5-2，code.claude.com 的 model-config、changelog、fast-mode、advisor，發佈文，以及 Artificial Analysis、Cognition FrontierCode 2.0、CursorBench、ARC Prize、Vals、MathArena、Mercor 的排行榜。證據檔：scratchpad `fable52-evidence.json`（card、官方文件與第三方合計 595 條核對過的發現；card 另有 56 條、官方文件另有 10 條沒核對）、`fable52-digest3.md`（重要度 3 的摘要）、`dl-fable52-card\card.txt`（card 文字，頁碼為 PDF 頁）。scratchpad 路徑是 `C:\Users\stans\AppData\Local\Temp\claude\699e9a5357b24d78\d212261e-df19-4adb-aeec-19a1320990b0\scratchpad\`，重開機或清理可能會消失。當天只寫提案（7 到 12），沒改 router。

2026-11-23：Stan 核可提案，router 換成 Fable 5.2 版（Claude Code v2.1.321）。改了：Fable 5.2 取代 Fable 5.1 當升級模型（high 起、長程 agentic coding 用 xhigh、max 不當預設）；刪掉「CursorBench 上 Opus 5.5 每一檔都贏 Fable max」這類 Fable 5.1 時期的結論，改成 Fable 5.2 贏與輸的清單；新增硬規則 16「用 Fable 5.2 時的防護」與 `fable52-system-card.md`；Mythos 5.1 換成 Mythos 5.2 並寫資安分工；硬規則 2、3、4、7 補 Fable 5.2；AA 表換成 Intelligence Index v5.0.1；硬規則 3 的 FrontierCode 依據換成 Cognition 現行 2.0 數字；刪掉「fallback 影響應該很小」，改列 VulcanBench 與 card 的 fallback 比率；`opus55-system-card.md` 刪掉 `DISABLE_GROWTHBOOK=1` 那句（這個變數 2026-10-14 已移除），補 regex hook 與繼續做迴圈兩條；硬規則 15 存官方 Sonnet「做完就停」段原文，CLAUDE.md §2 fan-out 句指過來（v2.9）；Opus 5.5 主模型配 Fable 5.2 advisor 記為未採用。
- 當天收集的來源：artificialanalysis.ai 四個家族模型頁（`/models/claude-haiku-5-5`、`claude-sonnet-5-5`、`claude-opus-5-5`、`claude-fable-5-2`，抽 initialModels 數據，含逐項拆分）；https://cognition.com/frontiercode （資料檔 Last-Modified 2026-11-21）；vulcanbench.com 的 Opus 5.5、Haiku 5.5、Fable 5.2 研究頁與排行榜 CSV；platform.claude.com 的 prompting-claude-sonnet-5-5（「做完就停」段原文，Steer initiative and scope 節）與 prompting-claude-fable-5-2（Finish the whole task 節）。存檔在 scratchpad `dl-1123\`，抽取腳本在 `tools\`（`aa1123_*.py`）。
- Mythos 存取測試（2026-11-23 在主 session 實跑，輸出沒存檔）：`claude -p --model claude-mythos-5-2` 回答「ok」，`modelUsage` 顯示 `claude-mythos-5-2`。
- 同日複核後修正：硬規則 11 改照 fast-mode 文件（2026-11-14 讀，fast 與標準速度各用一份 cache，之後每次切換都重讀）；09-26 依 prompt-caching 文件寫的「之後都保 cache」，那份文件這次沒重讀。硬規則 9、12 補 Fable 5.2，硬規則 10 只補有證據的部分。fallback 比率分成攻擊測試與良性 coding 兩種寫。
- 觀察項：Haiku 5.5 xhigh。VulcanBench xhigh 22/23 題、每題 0.84 美元、19.0 分鐘，比 high（17/23、1.25 美元、26.8 分鐘）好又省；AA high 29.9 → xhigh 34.6。規則仍是不開 xhigh，數據在 `effort-evidence.md`「觀察項」。
- 未驗證項：
  - Mythos 5.2 走哪個週額度桶。
  - Fable 5.2 吃不吃 user settings 頂層 `effortLevel`（model-config 只點名 Opus 5、Fable 5.1 與更早的模型會吃、Opus 5.5 不吃）。
  - Claude Code 裡 Fable 5.2 中途換 effort 是否保 cache（API 的 per-message effort 有保，CC 文件沒寫）；CC 裡 Opus 5.5 → Fable 5.2 是否保留推理（API 文件說 Fable 5.2 讀得懂 Opus 5.5 的 block）。
  - Fable 5.2 在 `modelSettings` 裡的鍵名（文件只說逐模型存，沒寫鍵名）。
  - Fable 5.2 的 `reasoning_extraction` refusal 會不會走 server-side fallback（證據檔這條沒核對）。
  - AA 的「Default Fallback」標籤是什麼意思：Sonnet、Opus、Fable 5.2 每個變體都有，Haiku 沒有，頁面沒定義。
  - FrontierCode 2.0 的兩套數字：Fable 5.2 card（SC pdf 209）是 Cognition 2026-11-11 重算前的版本（Fable 5.2 xhigh 49.1、Opus 最佳 45.5），現行排行榜是 50.2 與 47.3；決策照現行榜，引 card 時註明版本。
  - Fable 5.2 在 CursorBench 的分數，Cursor 說有一部分來自 harness 改進，跟 Opus、Sonnet 的分數不完全可比。
  - AA 各檔位獨立網址 2026-11-23 起都轉回家族頁；Sonnet low 到 high、Haiku low 到 xhigh 只在一頁出現，沒有交叉核對。
  - VulcanBench 上 Mythos 5.2 沒有資料。
