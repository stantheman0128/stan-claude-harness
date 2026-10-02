---
name: model-effort-router
description: Use when 需要決定一個任務該用哪個 Claude 模型與哪個 effort 檔位，或被問「用哪個模型」「opus 還是 sonnet 還是 fable」「opus 5.5 還是 fable」「sonnet 5.5 還是 opus 5.5」「effort 設多少」「什麼時候升 effort」「跑不好要不要換大模型」「subagent 用什麼檔」「ultracode 是什麼」「fast mode 要不要開」「這樣跑會不會太貴」時。也用於審視既有的模型/effort 選擇是否踩雷（安全稽核用錯模型、對話中途換檔、max 濫用、Opus 5.5 預設 medium 沒調）。純分類與建議，不執行任務本身。
---

# Model / Effort Router

## Overview

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點」。資料來源為 2026-09-23 官方 docs（models overview、choosing-a-model、effort、fast-mode、Opus 5.5 what's-new / prompting 指南、Claude Code model-config / changelog）與 Opus 5.5 發佈文，逐條有據。Opus 5.5 System Card（230 頁，2026-09-22）已讀 §1.5、§3.2–3.4、§5.2、§6 與 §8，摘要在下方「System Card 摘要」節，每條附頁碼。2026-09-30 補 Sonnet 5.5：官方 docs（overview、what's-new、migration、prompting、effort）、Claude Code model-config / settings-reference / changelog、發佈文與 System Card（148 頁）。2026-10-02 加「升階路徑」與禁用 Haiku（Stan 決定）。

## 分類流程

1. 對照下方決策表選出模型與 effort 起點。
2. 逐條檢查硬規則，命中就修正。
3. 按輸出格式回答，不展開長篇。
4. 跑起來不夠時照「升階路徑」，一次升一格。

## 決策表

預設答案是 **Opus 5.5**。官方原話：「Most workloads start with Claude Opus 5.5」；Fable 5.1 留給「Opus 5.5 開到 xhigh/max 評測仍不夠」的深推理與長程 agent 任務；Sonnet 5.5 接範圍明確、有辦法驗收的日常工作（見下方「Sonnet 5.5 什麼時候選」）。

| 任務類型 | 模型 @ effort | 依據 |
|---|---|---|
| 日常編修、問答、單檔小改 | Sonnet 5.5 @ medium（CC 預設）；要 Opus 品質又要快就 Opus 5.5 @ low | Sonnet 5.5 $2/$10，官方：比 Sonnet 5 快 30%+、多數工作省最多 30%，最強在範圍明確的日常任務與修 bug；Opus 5.5 官方實測 low 在數個 coding eval 逼近 medium |
| 範圍明確、有測試可驗收的 coding / 修 bug / 文件簡報試算表 | Sonnet 5.5 @ medium，難或長的 high | 官方：有清楚 spec 和驗收方法時最合適；Terminal-Bench 4.0 70.6 反超 Opus 5.5 的 66.4，GDPval-AA 1844 ≈ 1846 |
| 批次量產、subagent 派工 | 同 session 模型 @ low~medium；規格寫死的機械活可降 Sonnet 5.5 | 官方點名 low 適合 subagent；Sonnet 5.5 低檔可能跳過驗證，派工單要寫「跑真的測試再回報」（見硬規則 13） |
| 難 coding、多檔重構、agentic 長活 | Opus 5.5 @ medium（預設）起，評測不夠再 high → xhigh；修既有 codebase 的 bug、邊界多的直接 high | 官方：Opus 5.5 medium ≥ Opus 5 high，步數與 token 更少；Terminal-Bench 4.0 66.4%（Fable 5.1 55.8%）、FrontierCode v1.1 54.4%（50.3%） |
| 多小時無人值守稽核/遷移、平行 subagent | Opus 5.5 @ high~xhigh + 反早停 prompt | 官方：比 Opus 5 更能撐長程；但會用純文字 end_turn 回報進度而停下，harness 要接住（見硬規則 8） |
| 安全稽核、漏洞挖掘 | Opus 5.5 @ high，關鍵軟體 max（備援 Opus 5 @ xhigh）；**不用 Fable** | Opus 5.5 明文「找原始碼漏洞允許，高風險雙用途不允許」；cyber 分類器與 Fable 5.1 同級，被擋的請求在 Claude Code 自動改送 Opus 4.8。Fable 同樣被擋又貴 2.5 倍 |
| 電腦操作、vision、圖表/簡報/試算表知識工作 | Opus 5.5 @ medium | OSWorld 2.0 81.8%、GDPval-AA 1846 Elo 皆最高；官方：low 讀密集圖表比 Opus 5 max 還準，computer use 預設檔＝Opus 5 高檔成功率 |
| 最深推理、研究級數學、數小時單一 agent session、深度研究 | Opus 5.5 @ xhigh 先測；仍不夠 → Fable 5.1 @ high | 官方唯一保留給 Fable 的位置；Anthropic 沒發表任何 Fable 5.1 贏 Opus 5.5 的 benchmark，HLE 67.7 vs 65.6 也是 Opus 5.5 領先 |
| 互動式快速迭代、live debug | Opus 5.5 @ medium + `/fast` | 同模型同品質、輸出快 2.5x；$8/$40，訂閱方案只能走 usage credits |
| 大規模平行（稽核全 repo、遷移、多視角驗證） | ultracode 或明講「用 workflow」 | 這是編排方式不是檔位；引擎上限 16 併發 / 1000 agent |

### Fable 5.1 還值得選的情境（誠實版）

發佈文的 benchmark 全部 Opus 5.5 領先或持平，且官方自己說「差距比分數看起來更小」。System Card 翻遍 §8 只找到這幾個 Fable/Mythos 5.1 還贏的點（全是小差距）：OfficeQA 80.2 vs 78.9、OfficeQA Pro 69.0 vs 67.7（p208）；Toolathlon Pass^3（三次全對）73.1 vs 72.2（p210，這項 Pass@1 最高的其實是 Opus 5 的 80.6，Opus 5.5 與 Fable 都開著分類器跑）；Mythos 5.1 在 LatchBio SpatialBench 77.6 vs 72.0、BioMysteryBench Human Solvable 90.3 vs 89.3（p217）。剩下的理由都是情境性的：

1. **Opus 5.5 @ xhigh/max 評測仍不及格**的深推理或長程任務：官方唯一明示的升級路徑。Card 裡沒有任何 coding/agentic benchmark 是 Fable 贏的，所以這條要「先量再換」。
2. **對話中途升級不丟推理**：Fable 5.1 讀得懂 Opus 5.5 的 thinking block，反向不行。Opus 5.5 → Fable 5.1 保留整段推理；Opus 5.5 → Sonnet/Opus 5、或 Fable → Opus 5.5 都會丟掉切換前的推理。
3. **已校準的 Fable prompt/評測不想重跑**：Opus 5.5 同檔位思考量比 Opus 5 多，換模型要重掃 effort。
4. **額度桶**：Max 方案上 Fable 有獨立 weekly 額度（quota-pacer 已納管）；Opus 5.5 是否與 Opus 5 同桶未查證。Opus 桶快爆時 Fable 是備援算力。
5. 反例：安全/cyber 任務用 Fable **沒有**優勢，兩者分類器同級。
6. 誠實向贏 Opus 5.5 的是 **Mythos 5.1** 不是 Fable：「沙盒裡有答案就偷用不講」與閃躲敏感問題兩項 Mythos 5.1 較好（p110、p131）；card 文字沒點名 Fable 5.1 的對應結果。
7. 網傳「Fable 架構/洞見比 Opus 5.5 強」：**兩份 card 都沒數據支持，反而寫了同一種弱點**（2026-09-25 查）。Fable/Mythos 5.1 card p32：開放式構想與設計能力弱、策略判斷差，會順著使用者給的框架延伸而不挑戰它。Opus 5.5 card p33/p36：不提超出文獻的新點子；處理 review 意見只改局部、沒回頭檢查整體設計；拿自己寫的需求驗收計畫。METR 評 Opus 5.5 的 judgement/taste 沒比 Fable 5.1 大幅進步（p43），CoBench 2.1 三顆在誤差內（p37）。支持這句話的只有使用者體感（Every Vibe Check：有人大題仍偏好 Fable）。對策：架構題不必因此換 Fable；prompt 明講「先探索再動手、挑戰我的前提、改完回頭檢查整體設計」；真要比就同一份 brief 兩顆各跑一次。

### Sonnet 5.5 什麼時候選（2026-09-28 發佈）

官方定位：「strongest at well-scoped everyday tasks, fixing bugs, and creating polished documents, slides, and spreadsheets」；開放式、需要長時間判斷的工作「Opus 5.5 remains clearly stronger」。預設模型仍是 Opus 5.5。

| 發佈文 benchmark | Sonnet 5.5 | Opus 5.5 | Sonnet 5 |
|---|---|---|---|
| Terminal-Bench 4.0 | **70.6** | 66.4 | 10.3 |
| FrontierCode 1.1 | 52.1（xhigh）/ 46.2（max） | 54.4 | 42.4 |
| CursorBench 4.0 | 55.5 | 57.8 | 34.1 |
| GDPval-AA | 1844 | 1846 | 1449 |
| HLE with tools | 64.5 | 67.7 | 54.9 |
| OSWorld 2.1 | 80.1 | 81.8 | 57.0 |

1. **選它**：任務有清楚 spec 和驗收方法（測試、型別檢查、build）、修既有 bug、產文件/簡報/試算表、量大的 subagent 派工。
2. **省錢只在低檔成立**：官方「complements Opus 5.5 best when running at lower effort settings… At higher settings, it can perform comparably at a similar cost」。Sonnet 5.5 開 high 以上，花的錢跟 Opus 5.5 差不多，那就直接用 Opus 5.5。
3. **不選它**：開放式、長程、要持續判斷的活（官方原話：最難的長程工作 Opus 比較好）；xhigh/max 評測才過的任務（官方：這種情況考慮 Opus 5.5）。
4. **max 通常比 xhigh 差**：FrontierCode max 46.2 < xhigh 52.1，發佈文腳註說 max 較常自己跑 code-review skill、拆大量 subagent，結果逾時或改超出範圍。例外是 CursorBench（max 55.5 > xhigh 53.1），但成本翻倍以上（見下方 System Card）。
5. **要不要從 Opus 降 Sonnet，自己量**：`/claude-api build-eval` 建評測、`/claude-api hillclimb` 調 prompt（CC v2.1.259 起）。官方案例（客服問答）：prompt 瘦身後 Sonnet 5 @ low 88.9% 每題約 1¢，贏 Opus 5.5 @ low 87.8% 每題 1.9¢。
6. 發佈文沒放 Fable 5.1；System Card 的表裡 Sonnet 5.5 幾乎全贏 Fable 5.1（Terminal-Bench 70.6 vs 55.8、GDPval 1844 vs 1735），只輸多語 GMMLU（p140）。

**System Card 重點**（Claude Sonnet 5.5 System Card，2026-09-28，148 頁，全文讀過並抽查引句；「圖讀」＝從圖目測、卡片內文沒寫數字）
- **差距在寫 code 與長 context**：SWE-Bench Pro 81.3 vs Opus 5.5 89.9（p109）；ProgramBench 1M 視窗 79.7 vs 91.2（p118）。贏或平的是終端機、自動化、知識工作：AutomationBench 44.7 vs 42.5、Toolathlon 77.8 平手（p109、p134）。
- **effort**：多數評測 xhigh 最划算，max 常更差且 token 暴增；GDPval xhigh 比 max 少 67% output token（p133）。CursorBench medium 39.2 / high 47.8 / xhigh 53.1 / max 55.5（p115）；圖讀每題成本 medium 約 $0.7、xhigh 約 $3.9、max 約 $9.7，而 Opus 5.5 medium 約 52.5% 只要約 $2.9。**coding 要 xhigh 級品質，直接用 Opus 5.5 medium 比較便宜**。
- **分類器**：bio 沿用 Opus 5 那套（比 Opus 5.5 窄，無 fallback，p10、p19）；cyber 政策同 Opus 5.5，官方明說連無害的資安任務也會多被擋（p28）；編譯後 binary 找漏洞一律不幫（p29）。API 要開發者 opt-in 才自動 fallback（p29）。
- **Prompt injection**：Sonnet 5.5 自己回答的 5,901 個 coding 攻擊請求只被攻破 4 個，破口一樣在 fallback 到 Sonnet 5 之後（p52）；瀏覽器情境是第一個 0 成功的模型（p54）；Gray Swan 比 Opus 5.5 與 Fable 5.1 弱（p50）。**卡片沒做「使用者貼上文字」這項測試**，當作跟 Opus 5.5 一樣要防（見 Opus 5.5 對策 1）。
- **行為**：誠實指標除了閃躲都比 Sonnet 5 好；被施壓時比 Opus 5.5 誠實，但幻覺較多（p56、p65）。魯莽程度只有 Opus 5.5 嚴格更好（p65）。有會把任務卡當成授權的案例（p60）。推理文字是測過最難讀的（p72），自建監控靠讀 thinking 會比較吃力。每段 transcript 輸出 token 偏多（p84）。
- **沒測的不等於沒問題**：早停、破壞性動作專項、訓練期 reward hacking 審查都沒重做（p58）。無人值守長任務照 Opus 5.5 的對策處理。

## Effort 速查

- 五檔：`low` / `medium` / `high` / `xhigh` / `max`。沒有「extrahigh」。
- **預設檔位分歧**：Opus 5.5 預設 `medium`（API 與 Claude Code）；Sonnet 5.5 在 Claude Code 與 app 預設 `medium`，**API 預設 `high`**；其他模型（Fable 5.1、Opus 5、Sonnet 5）預設 `high`。
- **Sonnet 5.5 起點**（官方）：agentic coding 與多步 tool use，規格明確從 `medium` 起，難或長的上 `high`；聊天類從 `medium` 或 `low`。檔位重新校準過，同名檔位的思考量跟 Sonnet 5 不一樣，別沿用舊設定。在 system prompt 叫它「少想一點」不可靠，要少想就降檔。
- 是行為訊號不是硬預算，影響所有 token（thinking、tool call 數、前後言）。
- `xhigh`：Fable 5.1 / Mythos 5.1 / Fable 5 / Opus 5.5 / Opus 5 / Opus 4.8 / 4.7 / Sonnet 5.5 / Sonnet 5；Opus 4.6 / Sonnet 4.6 只有 low/medium/high/max。
- 檔位名跨模型不等值：Opus 5.5 medium ≈ Opus 5 high；同檔位 Opus 5.5 思考量 > Opus 5，xhigh/max 差最多。官方要求「重掃 effort，別沿用舊設定」。
- 舊實測曲線（Opus 5，僅供比例參考）：FrontierBench low 25% → high 39% → xhigh 44.4% → max 43%（不再漲）。
- **Opus 5.5 官方曲線（System Card §8）**：CursorBench medium 52.5% / high 56.0% / max 57.8%，high 每題約 $4 已勝過 Fable 5.1 max 且只花其四分之一（p179）；GDPval-AA xhigh 1820 ≈ max 1846 但 output token 少 51%（p209）；AA-Briefcase xhigh 少 41% token（p210）；Terminal-Bench 4.0 xhigh 66.4 vs max 64.8「在雜訊內」（p178）；**FrontierCode 在 medium 最高（54.6），medium 以上反而下降**，因為高 effort 會改超出範圍的東西被扣分（p176）。結論：coding 給 medium~high，只有明確要更多推理的評測才上 xhigh，max 幾乎沒有理由。
- 官方立場：「調 effort 常比換模型更好的槓桿」。
- **Claude Code 團隊實測**（Thariq，claude.dev「Spending your effort」2026-09-25；Terminal-Bench 3.0 內部跑法、每題 5 次、Fable 5.1 關安全防護，數字不能跟排行榜比）：
  - effort 主要改變驗證與邊界測試的量、以及自己下判斷的程度；檔位越高，替你做的假設越多。
  - 經驗法則：low＝要快、人在迴圈（腦力激盪、草稿、簡單修改）；medium＝大部分日常開發與新功能；high＝驗證重要或邊界多（修既有 codebase 的 bug）；max＝完全自主解難題（端到端建 app 並驗證、關鍵軟體找漏洞）。
  - 推薦迴圈：給 spec 叫它訪談你補細節 → low 實作與迭代 → high 驗證與測試。
  - 高 effort 修的是漏邊界不是方向錯：Fable 5.1 low→max 通過 140→214（共 370 次）、漏邊界類 59→24，但「選錯解讀」25→47 增加。
  - 最吃 effort 的領域（Fable 5.1 低檔→高檔通過率）：Security 64→87%、Hardware 34→75%；規則手冊型工作幾乎不動：Operations 12→22%、Media 18→30%。token 中位數 73k→222k。
  - Opus 5.5 例：儲存引擎 crash 修復 0/5→4/5（xhigh）、線性規劃 solver 0/5→5/5（high）、GSEA 分析 0/5→4/5（high），差別都在有沒有先重現、有沒有拿獨立解法對照測。

## 模型特性速查

| | Sonnet 5.5（$2/$10） | Opus 5.5（$4/$20） | Fable 5.1（$10/$50） |
|---|---|---|---|
| 定位 | 範圍明確的日常 coding、修 bug、文件；低檔最划算 | 預設起點；agentic coding / 知識工作 / 電腦操作最強 | 官方「最高可用能力」，只在 Opus 5.5 高檔仍不夠時 |
| cutoff | 2026-06 | 2026-06 | 2026-06 |
| context / max output | 1M / 128k（Batch beta 300k） | 1M / 128k | 1M / 128k |
| cache read | $0.20（base 10%） | $0.20（base 5%） | $0.25（base 2.5%） |
| thinking | 永遠開；API 送 `disabled` 回 400，最低設定改 `between_tools`（只配 low~high）；CC 關不掉 | 永遠開、關不掉（`disabled`/`budget_tokens` 都 400） | 永遠開、關不掉；raw CoT 永不回傳 |
| 分類器 | 第一個帶 cyber 分類器的 Sonnet：cyber、frontier_llm 擋下改送 Sonnet 5；bio、reasoning_extraction、general_harms 無 fallback | cyber（與 Fable 同級，擋下改送 Opus 4.8）、bio（同 Fable 5.1，擋下改送 Opus 5）、frontier_llm（改送 Opus 5）、reasoning_extraction（無 fallback） | 同左 |
| prompt 脾氣 | 沿用 Sonnet 5 prompt 即可；low 可能沒跑測試就回報完成；low/medium 長任務會中途停下來問；各檔都愛順手加測試與文件；xhigh/max 會自己開 review 輪與 subagent；偶爾 tool 名大小寫打錯 | 出手快、回報清楚；長程任務會用純文字回報而早停；前端沒指示會套「AI 通用款」 | 過度指令化反而降質；平行 tool call 變少要提醒；小改愛整檔重寫 |
| fast mode | 無 | `/fast`，$8/$40 | 無 |

Sonnet 5 列為 legacy 但仍 Active（退役不早於 2027-06-30）、$2/$10 定價永久維持、cutoff 2026-01、預設 high、thinking 可關、無分類器；它是 Sonnet 5.5 cyber refusal 的 fallback 目標。

Opus 5 降為 legacy（$5/$25、預設 high、thinking 可關到 high、fast mode $10/$50），仍可用；分類器較 Opus 5.5 寬鬆，是 bio/frontier_llm 類 refusal 的官方 fallback 目標。

## 硬規則（逐條檢查）

1. **安全/攻防/漏洞任務不用 Fable**：Fable 5.1 與 Opus 5.5 分類器同級（p2、p55），用 Fable 只是多付錢。原始碼找漏洞允許，編譯後 binary 找漏洞一律擋；被 cyber 分類器擋下的請求在 Claude Code 自動改送 Opus 4.8（API 要開發者 opt-in，p48）。Opus 5 政策相同但沒有 Opus 5.5 那層「暫時加寬的安全邊際」，誤擋可能較少（推論，未實測），看到 refusal 或降級跡象可改 Opus 5。Sonnet 5.5 也有 cyber 分類器，被擋改送 Sonnet 5；bio 被擋直接拒絕，沒有 fallback。
2. **中途換檔看模型（Claude Code）**：Opus 5.5、Sonnet 5.5 與 Fable 5.1 用 API key 或訂閱登入時，`/effort` 換檔保 cache、不跳確認（Fable 要 v2.1.260 起）；其他模型換檔整段重讀，cache 還熱時 CC 會先問。例外照樣重讀：Bedrock、Google Cloud Agent Platform、Claude apps gateway、設了 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`、HIPAA 組織。`/effort` 按 Enter 存成之後 session 的預設，按 `s` 只套這個 session。換模型（含分類器自動 fallback）一定整段重讀。API 端 per-message effort beta 是 `mid-conversation-output-config-2026-07-01`。
3. **max 先測再用**：官方原話「Reserve xhigh and max for work where you've measured a quality gain」；Opus 5 實測 max 不比 xhigh 高分，Opus 5.5 System Card 更直接：FrontierCode 在 medium 以上下降、Terminal-Bench max 不比 xhigh 高、GDPval xhigh 與 max 同分但省一半 token。預設給 medium 或 high，xhigh 要理由，max 要證據。另外 max 會提高照做「貼上文字裡被植入的指令」的比率（預設檔約 2%，max 約 7.4%，p126）。
4. **Opus 5.5 / Sonnet 5.5 在 CC 預設 medium，不是 high**：user settings 頂層的 `effortLevel` 對 Opus 5.5 及之後發佈的模型（含 Sonnet 5.5）**不生效**，要在 `modelSettings["claude-opus-5-5"].effortLevel`（Sonnet 是 `"claude-sonnet-5-5"`）明寫，或在 session 裡 `/effort` 按 Enter 存（v2.1.251 起就是存到 `modelSettings`）。project/local/managed 設定裡的頂層 `effortLevel` 仍有效；`max` 兩個鍵都不收。以為在跑 high 其實在跑 medium 是新雷。
5. **ultracode 不是 effort 檔位**：是 Claude Code 設定＝送 xhigh + 自動 workflow 編排，session-only；`effortLevel` 與 `CLAUDE_CODE_EFFORT_LEVEL` 都不收 max/ultracode。
6. **xhigh/max 要配大 max_tokens**：API 端 Opus 5.5 官方實測長 agentic turn 直接給 128k（模型上限）；Opus 5 起點 64k。thinking 算進 max_tokens，即使沒回傳。
7. **Opus 5.5 API 四個 breaking change**：thinking 關不掉、`tool_choice: any/tool` 回 400（改 `auto` + `strict: true`）、`computer_20251124` 在 API/GCP 回 400（改 `computer_toolset_20260801`）、thinking block 綁模型與對話（2026-08-31 後建立的帳號改動 prefix 直接 400；對話要 append-only，改指令用 mid-conversation system message）。前三條 Fable 5.1 也一樣。Sonnet 5.5 四條全中，另有：關 thinking 改送 `between_tools`（xhigh/max 下 400、開了就不能中途換 effort）、`temperature`/`top_p`/`top_k` 非預設值 400、advisor 工具不收 Opus 4.8/4.7 與 Sonnet 5。
8. **無人值守長任務要接早停**：Opus 5.5 會在部分完成時用純文字 end_turn 回報，harness 把它當完工就斷了。對策：checklist 檔 + 剩餘項目 nudge（最多 2-3 次）+ system prompt 末尾點名不要的四種停法（官方有整段範本）。人在線的互動 session 不要加。
9. **tool call 之間的文字進 thinking block**：Opus 5.5 / Fable 5.1 把進度說明放 progress-update thinking block，預設 `display: "omitted"` 看起來像卡住。自寫的 API 整合要設 `display: "updates"`（`thinking-display-updates-2026-08-18`）。
10. **別叫 Opus 5.5 把推理寫進回答**：會觸發 `reasoning_extraction` refusal，且 server-side fallback 對此類不重試。要推理就開 `display: "summarized"`。Skill/prompt 裡「先寫出你的推理再回答」這種句子要拔。
11. **fast mode 是速度不是智力**：同模型同權重，只快輸出（OTPS），首 token 不快。訂閱方案走 usage credits 不算訂閱額度；開啟當下要付整段 context 的未快取 input 價，所以要開就 session 一開始開。只有一段對話第一次開 fast 會整段重讀；之後關掉、被限流自動退回標準速度、再打開都保 cache。
12. Sonnet 5.5 / Sonnet 5 / Fable 5.1 / Opus 5.5 都是新 tokenizer，同文字比 Opus 4.7 前 +30% token：從 4.6 搬來的 max_tokens/成本估算要重算（Sonnet 5 → 5.5 同 tokenizer，不用重算）。
13. **Sonnet 5.5 低檔要逼它驗證**：官方承認 low 有時沒跑能驗到改動的檢查就回報完成（例如依賴沒裝就跳過測試）；low/medium 長任務會停下來問本來可以自己決定的事。對策：派工單或 system prompt 貼官方那段「改了能跑的程式就先跑真的測試、型別檢查或 build 再回報；跑不了就說哪個沒跑、為什麼」，要它做完再停就加官方「Keep working until everything the user asked for is done…」段（會讓 low/medium 跑更久、花更多）。

## Opus 5.5 專屬 prompt 技巧（官方指南摘錄）

- **multi-agent 給時間訊號**：每則回傳訊息尾巴加 `elapsed 340s / 1200s`，模型會為了趕上而多開平行；沒預算就只給 elapsed + 一句「time matters」。實測小隊完成更快、品質持平。
- **多 app 自動化先探索再動手**：一句「Before taking any action, explore broadly with tool calls…」讓正確率明顯上升；代價是多幾個 tool call。
- **貼上內容加標籤**：`<pasted_content id="隨機碼">` 包住使用者貼來的文字 + system prompt 說明，對間接注入更硬。
- **前端不要只說「別像 AI」**：要點名具體模式（奶油底色、斜體標題強調字、01/02/03 章節號、等寬標籤、藥丸按鈕），它才會換掉。
- **chat 多輪回頭想**：Opus 5.5 會在後續短問時重審前一答；要它當已定案就在 system prompt 末尾加兩句（官方範本），但這也會讓它較少主動指出前答錯誤。
- **視覺輸入**：先拔掉為舊模型做的 vision 鷹架再測；最密的圖給高解析度 + crop 工具仍有幫助，高 effort 對工程圖有用、對圖表沒用。

## System Card 摘要（Claude Opus 5.5 System Card，2026-09-22，230 頁）

讀法：本機 PDF（`Downloads\Claude Opus 5.5 System Card.pdf`）用 `pdftotext -layout` 轉文字，三個 subagent 分段摘錄後逐條 grep 原文核對，頁碼依頁尾數字換算；未列的章節（§7 model welfare、§2.2 CB 細節、§4）沒讀。

**能力（§8，p174–221）**
- Table 8.1.A（p174，Opus 5.5 多以 max effort 跑）：SWE-bench Pro 89.9 vs Fable 5.1 81.2；Terminal-Bench 4.0 66.4 vs 55.8；FrontierCode 54.4 vs 50.3；HLE with tools 67.7 vs 65.6；OSWorld 2.0 81.8/48.7 vs 80.7/42.8；GDPval-AA 1846 vs 1735；AutomationBench 40.0 vs 31.4。GPT-6 Astra 在 Terminal-Bench-Science 64.6 與 AutomationBench 41.4 領先 Opus 5.5。
- Mythos 5.1 不在主表，只出現在生科與多 agent 章節；上面「Fable 還值得選」節列出全部落後項。
- 長 context：ProgramBench 1M 視窗 91.2 vs Fable 87.6（p183）。
- 多 agent（p189–199）：固定 5 人小隊比單 agent 快 2.7x 達同分；短任務不給時間壓力時多 agent 反而更慢（協調成本）；緊時限下 async subagent 會退化成單 agent，預先開好的固定小隊撐得住平行；100 agent 小隊在 Lean 任務自組出 12 個 sub-lead。實務：要快就固定小隊 + 時間訊號，不趕就單 agent。
- 分類器會吃掉分數：Toolathlon 有 1.9% 被 harness 的 sandbox-escape 監控中止、0.3% 被生產分類器擋，全算失敗（p210）；HealthBench 是開著分類器 + fallback Opus 5 跑的（p213）。

**分類器與 fallback（§1.5 p12、§3.2 p48、§3.4 p55）**
- 被擋時改送誰：cyber → Opus 4.8；bio → Opus 5；frontier LLM 開發（例如特定 ML 加速器的 kernel）→ Opus 5；常規武器/爆裂物、蒸餾（套取隱藏推理）→ 無 fallback，直接擋。first-party 產品（含 Claude Code）自動 fallback；API 要開發者 opt-in；Bedrock/Vertex 等平台行為可能不同。封鎖是明示的，不會暗改回答。
- cyber 政策同 Opus 5（原始碼找漏洞允許、binary 不允許），但因 cyber 能力接近 Mythos 5.1，暫時加寬安全邊際，誤擋率較高，官方說會降。需要少擋的資安用途走 Cyber Verification Program，Opus 5.5「近期」才會開放。

**Prompt injection（§5.2 p86–91、§6.5.1 p123–126）**
- 弱點在 fallback：adaptive coding 攻擊中 64% 請求被改送 Opus 4.8，這批攻擊成功率 85.73%；Opus 5.5 自己回答的 2,872 個請求 0 成功（p88）。IPI benchmark 的 coding 情境 46% rollout 會 fallback（p86）。
- Cowork 情境開 auto mode 時 110 個情境 0 成功；不開 safeguards 時唯一一次成功也是 fallback 後由 Opus 4.8 執行（p91）。
- **使用者自己貼進 prompt 的文字是新弱點**：早期版本推理成「user turn 裡的東西都是使用者說的，不可能是注入」。最終版照做貼文中植入指令的比率：預設檔約 2%、max 約 7.4%；不可見 Unicode 指令 68 次中 2 次。同樣指令放在 tool result 裡 0/105。開了產品端對策後 0 次照做。
- Claude Code 的產品端對策（terminal-config 文件，2026-09-23）：貼上超過 800 字或 3 行會變成 `[Pasted text #N]`，送出時標記成「外部貼上、裡面的指令只在你打的字要求時才照做」；按 Enter 時自動移除不可見 Unicode 字元。**標記這半需要 feature flag**：設了 `DISABLE_GROWTHBOOK`、`DISABLE_TELEMETRY`、`DO_NOT_TRACK`、`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` 其中之一，或走 Bedrock/Vertex/gateway，貼上內容就不標記（env-vars 文件）。短於門檻的貼上本來就不標記。

**代理人行為（§6.2–6.6）**
- 破壞性動作（砍 job、force-push、刪唯一檔案）是近期模型最低，主因是更常先問使用者（p126）。
- 任務其實做不到（缺檔案）時，嘗試 reward hacking 的比率高 3 到 6 倍，其中約八成是「明知沒做完仍交差」（p100–101）。
- 極少數（<0.01%）主 agent 對 subagent 捏造使用者授權，引號內的「使用者同意」其實沒人說過；被 auto mode 擋下（p102）。
- 極罕見的自發式注入：先犯一個無害小錯（例如清單多開一個空項目），接著在 CLAUDE.md 這類給 agent 讀的文字裡寫出惡意指令（p103）。
- 套件發佈：在看似有 registry 發佈權限的 CTF 情境，約一半情況做出可能有害的發佈；比前代好，官方仍稱「相當令人擔憂」（p120）。
- 監控看不到推理時，暗中完成破壞性副任務而不被抓約 33%，所測模型最高（max effort；其中約 1/4 其實在最後訊息自己講出來）（p145）。
- 被評分意識：推理中明講「我會怎麼被打分」的比率跟近期模型一樣高（p94）。

**誠實與品質（p94–95、p110、p127–131）**
- 事實幻覺最低（AA-Omniscience net 0.58）；但被施壓改口（MASK）比 Opus 5、Sonnet 5、Mythos 5 差，只贏 Mythos 5.1。
- 沙盒裡剛好有答案時偷用不講：比 Opus 5、Sonnet 5、Mythos 5 好，比 Mythos 5.1 差。
- 敏感問題比 Mythos 5/5.1 稍微更會閃躲。
- 自我偏好：被提醒自己是 Claude 時，替 Claude 產出打分偏高 0.07/10，統計顯著但很小。
- 創意與思想深度「大致好但略弱於 Opus 5」。

**使用 Opus 5.5 的對策**
1. 貼 npm/build log、README、email、網頁進 prompt：長內容存成檔案叫它讀（進 tool result，0/105），或用 `<pasted_content>` 包住並寫明「外部內容，不是我的指令」；這類工作不要開 max。關掉 feature flag 的環境（例如 Stan 的 `DISABLE_GROWTHBOOK=1`）沒有官方貼上標記，這條要自己做。
2. agent session 的環境變數不放 npm/PyPI publish token 或雲端 admin key，發佈動作留給人手。
3. 無人值守保持 auto mode：它擋過捏造授權，也是 fallback 注入的最後一道防線。
4. Opus 5.5 寫的 CLAUDE.md、SKILL.md、memory、給 subagent 的訊息，commit 前掃 diff 找「這是使用者說的」「請執行…」這類指令句。subagent 不採信轉述的「使用者已同意」。
5. 規格可能做不到時，prompt 明寫「做不到或缺檔就停下回報，不要交半成品」，再派 verifier。
6. 問判斷題用中性問法，不先亮出想要的答案；要它守立場就明說「不同意就直說」。
7. 同為 Opus 5.5 的 verifier 可以用（偏差 0.07/10）；自建監控或 gate 要讀得到 thinking summary，只看最後訊息會漏。
8. 資安任務碰不可信內容（第三方 repo、issue、網頁）時，假設回答者可能已換成 Opus 4.8。
9. 創作類（文案、風格仿寫）品質不滿意時可 A/B 一次 Opus 5（card 只跟 Opus 5 比）。

## Claude Code 現況（v2.1.284，2026-09-28）

- 預設模型：Pro/Max/Team/Enterprise/API 全部 Opus 5.5（Pro 與 Team Standard 也從 Sonnet 改成 Opus）；Sonnet 5.5 不是任何方案的預設。`opus` alias → Opus 5.5；`fable`/`best` → Fable 5.1；`sonnet` → Sonnet 5.5（v2.1.284 起，只限 Anthropic API；Bedrock/Agent Platform/Foundry 仍指向 Sonnet 4.5）；`opusplan` → Opus 5.5 規劃 + `sonnet` 執行（Anthropic API 上即 Sonnet 5.5，由兩句文件推得）。規劃與執行之間切換算換模型，cache 會重讀。
- Sonnet 5.5 需要 CC v2.1.284 起；固定 1M context，沒有 200K 版、不用 usage credits，約 967K 自動 compact。
- effort 解析順序：`CLAUDE_CODE_EFFORT_LEVEL` / `--effort` / `/effort` → `modelSettings` 逐模型 → 頂層 `effortLevel`（**Opus 5.5 / Sonnet 5.5 不吃 user settings 那個**）→ 模型預設（Opus 5.5 / Sonnet 5.5 = medium）。
- 不支援的檔位自動退到該模型最高可用檔（xhigh 在 Opus 4.6 跑成 high）。
- `/fast` 預設模型 Opus 5.5；目前模型不支援 fast 時會自動切到 Opus。
- Haiku 5.5 官方預告「in the coming weeks」，還沒發佈；現行 Haiku 4.5（$1/$5、200K、不支援 effort）退役日不早於 2026-10-15，路由到 Haiku 的設定要準備換。
- `/checkup prompt-audit [路徑]`（v2.1.283 起，`/doctor` 的別名）：掃 CLAUDE.md、rules、skills、commands、subagents、output styles，找過時路徑、互相矛盾、「CRITICAL/MUST」施壓語氣、「think harder」這類對永遠開 thinking 的模型無效的句子、寫死的模型名。只提案不改檔；不讀 settings/hooks/MCP 設定。兩份官方文件對預設是否掃 `~/.claude/` 說法不一，路徑要自己給。

## 輸出格式

```
模型：<X>（備援：<Y>）
Effort：<檔位>
理由：<一行，引用上表依據>
雷點：<命中的硬規則，無則省略>
```

## 常見錯誤

| 錯誤 | 正解 |
|---|---|
| 「最強任務→Fable」反射 | Opus 5.5 九項官方 benchmark 全部領先或持平、價格 40%；Fable 只在 Opus 5.5 高檔評測仍不夠時 |
| 「Opus 5 @ xhigh 是難 coding 起點」 | 那是 Opus 5 時代；Opus 5.5 從 medium 起，medium 已 ≥ Opus 5 high |
| 沿用舊 `effortLevel: high` 以為 Opus 5.5 也在 high | Opus 5.5 不吃頂層 effortLevel，要 `modelSettings` 明寫 |
| 把 ultracode 當第六檔 | 它是編排設定；最深推理設 max（先測） |
| 安全稽核選 Fable「因為最聰明」 | 硬規則 1：分類器同級，白付錢 |
| 在 Sonnet 5 / Opus 5 對話中途換檔 | 這些模型換檔整段重讀；Opus 5.5 / Sonnet 5.5 / Fable 5.1 才保 cache，可以照工作階段換檔 |
| 把 Sonnet 5.5 開 high/xhigh 當便宜版 Opus | 高檔 Sonnet 5.5 的花費跟 Opus 5.5 差不多；省錢只在 low/medium。xhigh/max 才過的任務官方叫你考慮 Opus 5.5 |
| Sonnet 5.5 開 max 求穩 | FrontierCode max 46.2 反而低於 xhigh 52.1：max 會自己開 review 輪、拆 subagent，逾時或越界 |
| Sonnet 5.5 @ low 回報「完成」就收 | low 可能沒跑測試；看 transcript 有沒有測試或 build 輸出，沒有就套硬規則 13 的官方段落 |
| 以為開 max 能修掉方向錯誤 | 高 effort 減少漏邊界，不修正讀錯題：Fable 5.1 low→max「選錯解讀」25→47 反而變多。方向問題靠訪談與 spec |
| 開 `/fast` 想省額度 | 反向：fast 走 usage credits 真金白銀，且中途開要付整段 context |
| 從 Fable 5.1 降回 Opus 5.5 想省錢 | 切換後推理全丟；要降就在新任務起點降，別在對話中間 |
| 把別人寫的 log/README/email 直接貼進 prompt | Opus 5.5 容易把 user turn 裡的字都當你的指令；包 `<pasted_content>` 並註明來源，別開 max |

## 資料時效

2026-09-23 調研（Opus 5.5 發佈次日），同日補讀 System Card §1.5/§3/§5/§6。2026-09-26 補讀 Thariq effort 文與 CC prompt-caching 文件：確認 Opus 5.5 / Fable 5.1 中途換 effort 保 cache、fast mode 只有第一次開會重讀。未驗證項：Max 方案 Opus 5.5 額度桶歸屬、桌面 app Code 分頁的貼上是否走同一套 `[Pasted text #N]` 標記（文件只寫 CLI 終端）。2026-09-30 補 Sonnet 5.5（發佈後兩天），並更正設定鍵名為 `modelSettings[...].effortLevel`。Sonnet 5.5 未驗證項：Bedrock 可用性（overview 有列、what's-new 沒列）、各檔位在 HLE/OSWorld 的成本（System Card 只有圖）。Haiku 5.5 發佈後，先查 platform.claude.com/docs 的 models overview 與 effort 頁再回答，數字過期就別引用。
