---
name: model-effort-router
description: Use when 需要決定一個任務該用哪個 Claude 模型與哪個 effort 檔位，或被問「用哪個模型」「opus 還是 sonnet 還是 fable」「opus 5.5 還是 fable」「effort 設多少」「subagent 用什麼檔」「ultracode 是什麼」「fast mode 要不要開」「這樣跑會不會太貴」時。也用於審視既有的模型/effort 選擇是否踩雷（安全稽核用錯模型、對話中途換檔、max 濫用、Opus 5.5 預設 medium 沒調）。純分類與建議，不執行任務本身。
---

# Model / Effort Router

## Overview

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點」。資料來源為 2026-09-23 官方 docs（models overview、choosing-a-model、effort、fast-mode、Opus 5.5 what's-new / prompting 指南、Claude Code model-config / changelog）與 Opus 5.5 發佈文，逐條有據。Opus 5.5 System Card（230 頁，2026-09-22）已讀 §2–6 與 §8，摘要在下方「System Card 摘要」節，每條附頁碼。

## 分類流程

1. 對照下方決策表選出模型與 effort 起點。
2. 逐條檢查硬規則，命中就修正。
3. 按輸出格式回答，不展開長篇。

## 決策表

預設答案是 **Opus 5.5**。官方原話：「Most workloads start with Claude Opus 5.5」；Fable 5.1 留給「Opus 5.5 開到 xhigh/max 評測仍不夠」的深推理與長程 agent 任務。

| 任務類型 | 模型 @ effort | 依據 |
|---|---|---|
| 日常編修、問答、單檔小改 | Sonnet 5 @ high；要 Opus 品質又要快就 Opus 5.5 @ low | Sonnet 5 $2/$10 最便宜；Opus 5.5 官方實測 low 在數個 coding eval 逼近 medium、成本低很多 |
| 批次量產、subagent 派工 | 同 session 模型 @ low~medium | 官方點名 low 適合 subagent；低檔會合併 tool call、直接動手 |
| 難 coding、多檔重構、agentic 長活 | Opus 5.5 @ medium（預設）起，評測不夠再 high → xhigh | 官方：Opus 5.5 medium ≥ Opus 5 high，步數與 token 更少；Terminal-Bench 4.0 66.4%（Fable 5.1 55.8%）、FrontierCode v1.1 54.4%（50.3%） |
| 多小時無人值守稽核/遷移、平行 subagent | Opus 5.5 @ high~xhigh + 反早停 prompt | 官方：比 Opus 5 更能撐長程；但會用純文字 end_turn 回報進度而停下，harness 要接住（見硬規則 8） |
| 安全稽核、漏洞挖掘 | Opus 5.5 @ high（備援 Opus 5 @ xhigh）；**不用 Fable** | Opus 5.5 明文「找原始碼漏洞允許，高風險雙用途不允許」；cyber 分類器與 Fable 5.1 同級，大多數 cyber 任務會被改送 Opus 4.8。Fable 同樣被擋又貴 2.5 倍 |
| 電腦操作、vision、圖表/簡報/試算表知識工作 | Opus 5.5 @ medium | OSWorld 2.0 81.8%、GDPval-AA 1846 Elo 皆最高；官方：low 讀密集圖表比 Opus 5 max 還準，computer use 預設檔＝Opus 5 高檔成功率 |
| 最深推理、研究級數學、數小時單一 agent session、深度研究 | Opus 5.5 @ xhigh 先測；仍不夠 → Fable 5.1 @ high | 官方唯一保留給 Fable 的位置；Anthropic 沒發表任何 Fable 5.1 贏 Opus 5.5 的 benchmark，HLE 67.7 vs 65.6 也是 Opus 5.5 領先 |
| 互動式快速迭代、live debug | Opus 5.5 @ medium + `/fast` | 同模型同品質、輸出快 2.5x；$8/$40，訂閱方案只能走 usage credits |
| 大規模平行（稽核全 repo、遷移、多視角驗證） | ultracode 或明講「用 workflow」 | 這是編排方式不是檔位；引擎上限 16 併發 / 1000 agent |

### Fable 5.1 還值得選的情境（誠實版）

發佈文的 benchmark 全部 Opus 5.5 領先或持平，且官方自己說「差距比分數看起來更小」。System Card 翻遍 §8 只找到這幾個 Fable/Mythos 5.1 還贏的點（全是小差距）：OfficeQA 80.2 vs 78.9、OfficeQA Pro 69.0 vs 67.7（p208）；Toolathlon Pass3 73.1 vs 72.2（p210）；Mythos 5.1 在 LatchBio SpatialBench 77.6 vs 72.0、BioMysteryBench Human Solvable 90.3 vs 89.3（p217）。剩下的理由都是情境性的：

1. **Opus 5.5 @ xhigh/max 評測仍不及格**的深推理或長程任務：官方唯一明示的升級路徑。Card 裡沒有任何 coding/agentic benchmark 是 Fable 贏的，所以這條要「先量再換」。
2. **對話中途升級不丟推理**：Fable 5.1 讀得懂 Opus 5.5 的 thinking block，反向不行。Opus 5.5 → Fable 5.1 保留整段推理；Opus 5.5 → Sonnet/Opus 5、或 Fable → Opus 5.5 都會丟掉切換前的推理。
3. **已校準的 Fable prompt/評測不想重跑**：Opus 5.5 同檔位思考量比 Opus 5 多，換模型要重掃 effort。
4. **額度桶**：Max 方案上 Fable 有獨立 weekly 額度（quota-pacer 已納管）；Opus 5.5 是否與 Opus 5 同桶未查證。Opus 桶快爆時 Fable 是備援算力。
5. 反例：安全/cyber 任務用 Fable **沒有**優勢，兩者分類器同級。

## Effort 速查

- 五檔：`low` / `medium` / `high` / `xhigh` / `max`。沒有「extrahigh」。
- **預設檔位分歧**：Opus 5.5 預設 `medium`；其他所有模型（Fable 5.1、Opus 5、Sonnet 5）預設 `high`。API 與 Claude Code 皆如此。
- 是行為訊號不是硬預算，影響所有 token（thinking、tool call 數、前後言）。
- `xhigh`：Fable 5.1 / Mythos 5.1 / Fable 5 / Opus 5.5 / Opus 5 / Opus 4.8 / 4.7 / Sonnet 5；Opus 4.6 / Sonnet 4.6 只有 low/medium/high/max。
- 檔位名跨模型不等值：Opus 5.5 medium ≈ Opus 5 high；同檔位 Opus 5.5 思考量 > Opus 5，xhigh/max 差最多。官方要求「重掃 effort，別沿用舊設定」。
- 舊實測曲線（Opus 5，僅供比例參考）：FrontierBench low 25% → high 39% → xhigh 44.4% → max 43%（不再漲）。
- **Opus 5.5 官方曲線（System Card §8）**：CursorBench medium 52.5% / high 56.0% / max 57.8%，high 每題約 $4 已勝過 Fable 5.1 max 且只花其四分之一（p179）；GDPval-AA xhigh 1820 ≈ max 1846 但 output token 少 51%（p209）；AA-Briefcase xhigh 少 41% token（p210）；Terminal-Bench 4.0 xhigh 66.4 vs max 64.8「在雜訊內」（p178）；**FrontierCode 在 medium 最高（54.6），medium 以上反而下降**，因為高 effort 會改超出範圍的東西被扣分（p176）。結論：coding 給 medium~high，只有明確要更多推理的評測才上 xhigh，max 幾乎沒有理由。
- 官方立場：「調 effort 常比換模型更好的槓桿」。

## 模型特性速查

| | Sonnet 5（$2/$10） | Opus 5.5（$4/$20） | Fable 5.1（$10/$50） |
|---|---|---|---|
| 定位 | 量產工作馬，不推前沿 | 預設起點；agentic coding / 知識工作 / 電腦操作最強 | 官方「最高可用能力」，只在 Opus 5.5 高檔仍不夠時 |
| cutoff | 2026-01 | 2026-06 | 2026-06 |
| context / max output | 1M / 128k | 1M / 128k | 1M / 128k |
| cache read | $0.20 | $0.20（base 5%） | $0.25（base 2.5%） |
| thinking | adaptive 預設開，可關 | 永遠開、關不掉（`disabled`/`budget_tokens` 都 400） | 永遠開、關不掉；raw CoT 永不回傳 |
| 分類器 | 無 | cyber（與 Fable 同級，大多改送 Opus 4.8）、bio（同 Fable 5.1）、frontier_llm、reasoning_extraction | 同左 |
| prompt 脾氣 | 指令字面化服從，舊加重語氣會過度觸發 | 出手快、回報清楚；長程任務會用純文字回報而早停；前端沒指示會套「AI 通用款」 | 過度指令化反而降質；平行 tool call 變少要提醒；小改愛整檔重寫 |
| fast mode | 無 | `/fast`，$8/$40 | 無 |

Opus 5 降為 legacy（$5/$25、預設 high、thinking 可關到 high、fast mode $10/$50），仍可用；分類器較 Opus 5.5 寬鬆，是 bio/frontier_llm 類 refusal 的官方 fallback 目標。

## 硬規則（逐條檢查）

1. **安全/攻防/漏洞任務不用 Fable**：Fable 5.1 與 Opus 5.5 分類器同級，用 Fable 只是多付錢。原始碼層級找漏洞 Opus 5.5 允許；exploit/攻防類會被改送 Opus 4.8，看到 refusal 或降級跡象改 Opus 5。
2. **一段對話固定一檔（Claude Code）**：`/effort` 改頂層 effort 會重寫 rendered prompt、cache 全滅。API 端 Opus 5.5 / Fable 5.1 / Opus 5 有 per-message effort beta（`mid-conversation-output-config-2026-07-01`）可保 cache；Claude Code 是否走這條未查證，當作會滅。
3. **max 先測再用**：官方原話「Reserve xhigh and max for work where you've measured a quality gain」；Opus 5 實測 max 不比 xhigh 高分，Opus 5.5 System Card 更直接：FrontierCode 在 medium 以上下降、Terminal-Bench max 不比 xhigh 高、GDPval xhigh 與 max 同分但省一半 token。預設給 medium 或 high，xhigh 要理由，max 要證據。
4. **Opus 5.5 預設 medium，不是 high**：舊的 `effortLevel` 設定對 Opus 5.5 及之後的模型**不生效**（CC v2.1.280 起），要在 `modelSettings["claude-opus-5-5"].effort` 明寫。以為在跑 high 其實在跑 medium 是新雷。
5. **ultracode 不是 effort 檔位**：是 Claude Code 設定＝送 xhigh + 自動 workflow 編排，session-only；`effortLevel` 與 `CLAUDE_CODE_EFFORT_LEVEL` 都不收 max/ultracode。
6. **xhigh/max 要配大 max_tokens**：API 端 Opus 5.5 官方實測長 agentic turn 直接給 128k（模型上限）；Opus 5 起點 64k。thinking 算進 max_tokens，即使沒回傳。
7. **Opus 5.5 API 四個 breaking change**：thinking 關不掉、`tool_choice: any/tool` 回 400（改 `auto` + `strict: true`）、`computer_20251124` 在 API/GCP 回 400（改 `computer_toolset_20260801`）、thinking block 綁模型與對話（2026-08-31 後建立的帳號改動 prefix 直接 400；對話要 append-only，改指令用 mid-conversation system message）。前三條 Fable 5.1 也一樣。
8. **無人值守長任務要接早停**：Opus 5.5 會在部分完成時用純文字 end_turn 回報，harness 把它當完工就斷了。對策：checklist 檔 + 剩餘項目 nudge（最多 2-3 次）+ system prompt 末尾點名不要的四種停法（官方有整段範本）。人在線的互動 session 不要加。
9. **tool call 之間的文字進 thinking block**：Opus 5.5 / Fable 5.1 把進度說明放 progress-update thinking block，預設 `display: "omitted"` 看起來像卡住。自寫的 API 整合要設 `display: "updates"`（`thinking-display-updates-2026-08-18`）。
10. **別叫 Opus 5.5 把推理寫進回答**：會觸發 `reasoning_extraction` refusal，且 server-side fallback 對此類不重試。要推理就開 `display: "summarized"`。Skill/prompt 裡「先寫出你的推理再回答」這種句子要拔。
11. **fast mode 是速度不是智力**：同模型同權重，只快輸出（OTPS），首 token 不快。訂閱方案走 usage credits 不算訂閱額度；開啟當下要付整段 context 的未快取 input 價，所以要開就 session 一開始開。切 fast/standard 會 cache miss。
12. Sonnet 5 / Fable 5.1 / Opus 5.5 都是新 tokenizer，同文字比 Opus 4.7 前 +30% token：從 4.6 搬來的 max_tokens/成本估算要重算。

## Opus 5.5 專屬 prompt 技巧（官方指南摘錄）

- **multi-agent 給時間訊號**：每則回傳訊息尾巴加 `elapsed 340s / 1200s`，模型會為了趕上而多開平行；沒預算就只給 elapsed + 一句「time matters」。實測小隊完成更快、品質持平。
- **多 app 自動化先探索再動手**：一句「Before taking any action, explore broadly with tool calls…」讓正確率明顯上升；代價是多幾個 tool call。
- **貼上內容加標籤**：`<pasted_content id="隨機碼">` 包住使用者貼來的文字 + system prompt 說明，對間接注入更硬。
- **前端不要只說「別像 AI」**：要點名具體模式（奶油底色、斜體標題強調字、01/02/03 章節號、等寬標籤、藥丸按鈕），它才會換掉。
- **chat 多輪回頭想**：Opus 5.5 會在後續短問時重審前一答；要它當已定案就在 system prompt 末尾加兩句（官方範本），但這也會讓它較少主動指出前答錯誤。
- **視覺輸入**：先拔掉為舊模型做的 vision 鷹架再測；最密的圖給高解析度 + crop 工具仍有幫助，高 effort 對工程圖有用、對圖表沒用。

## System Card 摘要（Claude Opus 5.5 System Card，2026-09-22，230 頁）

讀法：Google Docs Viewer 轉文字 + 三個 subagent 分段摘錄，數字皆附頁碼；未列的章節（§7 model welfare、§2.2 CB 細節）沒讀。

**能力（§8，p174–221）**
- Table 8.1.A（p174，Opus 5.5 多以 max effort 跑）：SWE-bench Pro 89.9 vs Fable 5.1 81.2；Terminal-Bench 4.0 66.4 vs 55.8；FrontierCode 54.4 vs 50.3；HLE with tools 67.7 vs 65.6；OSWorld 2.0 81.8/48.7 vs 80.7/42.8；GDPval-AA 1846 vs 1735；AutomationBench 40.0 vs 31.4。GPT-6 Astra 在 Terminal-Bench-Science 64.6 與 AutomationBench 41.4 領先 Opus 5.5。
- Mythos 5.1 不在主表，只出現在生科與多 agent 章節；上面「Fable 還值得選」節列出全部落後項。
- 長 context：ProgramBench 1M 視窗 91.2 vs Fable 87.6（p183）。
- 多 agent（p189–199）：固定 5 人小隊比單 agent 快 2.7x 達同分；短任務不給時間壓力時多 agent 反而更慢（協調成本）；緊時限下 async subagent 會退化成單 agent，預先開好的固定小隊撐得住平行；100 agent 小隊在 Lean 任務自組出 12 個 sub-lead。實務：要快就固定小隊 + 時間訊號，不趕就單 agent。
- 分類器會吃掉分數：Toolathlon 有 1.9% 被 harness 的 sandbox-escape 監控中止、0.3% 被生產分類器擋，全算失敗（p210）；HealthBench 是開著分類器 + fallback Opus 5 跑的（p213）。

## Claude Code 現況（v2.1.280，2026-09-22）

- 預設模型：Pro/Max/Team/Enterprise/API 全部 Opus 5.5（Pro 與 Team Standard 也從 Sonnet 改成 Opus）。`opus` alias → Opus 5.5；`fable`/`best` → Fable 5.1；`opusplan` → Opus 5.5 規劃 + Sonnet 5 執行。
- effort 解析順序：`CLAUDE_CODE_EFFORT_LEVEL` / `--effort` / `/effort` → `modelSettings` 逐模型 → 頂層 `effortLevel`（**Opus 5.5 不吃**）→ 模型預設（Opus 5.5 = medium）。
- 不支援的檔位自動退到該模型最高可用檔（xhigh 在 Opus 4.6 跑成 high）。
- `/fast` 預設模型 Opus 5.5；目前模型不支援 fast 時會自動切到 Opus。
- Sonnet 5.5 / Haiku 5.5 官方預告「幾週內」；出了要回頭改 Sonnet 那一列。

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
| 對話中途降檔省錢 | CC 端 cache 重寫反而更貴；API 端用 per-message effort |
| 開 `/fast` 想省額度 | 反向：fast 走 usage credits 真金白銀，且中途開要付整段 context |
| 從 Fable 5.1 降回 Opus 5.5 想省錢 | 切換後推理全丟；要降就在新任務起點降，別在對話中間 |

## 資料時效

2026-09-23 調研（Opus 5.5 發佈次日）。未驗證項：Max 方案 Opus 5.5 額度桶歸屬、Claude Code `/effort` 是否走 per-message effort。Sonnet 5.5 / Haiku 5.5 發佈後，先查 platform.claude.com/docs 的 models overview 與 effort 頁再回答，數字過期就別引用。
