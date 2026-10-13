---
name: model-effort-router
description: Use when 需要決定一個任務該用哪個 Claude 模型與哪個 effort 檔位，或被問「用哪個模型」「opus 還是 sonnet 還是 fable」「haiku 能不能用」「opus 5.5 還是 fable」「sonnet 5.5 還是 opus 5.5」「effort 設多少」「什麼時候升 effort」「跑不好要不要換大模型」「subagent 用什麼檔」「fan-out 帶什麼 effort」「ultracode 是什麼」「fast mode 要不要開」「這樣跑會不會太貴」時。也用於審視既有的模型/effort 選擇是否踩雷（安全稽核用錯模型、對話中途換檔、max 濫用、Sonnet 5.5 留在預設 medium、頂層 effortLevel 對 Opus 5.5 無效）。純分類與建議，不執行任務本身。
---

# Model / Effort Router

## Overview

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點 + 下一格」。本檔只放做決定要用的規則；數據、引句、頁碼與 API 細節放在 `references/`，被質疑、要引數字或寫 API 整合時才讀。資料截至 2026-10-13（Claude Code v2.1.296）。

**Stan 的取捨（2026-10-13 定案）：品質優先。** 升一檔只要實際多拿到分數，寧可多花 token。判斷標準是「升一檔多拿到什麼」，不是「每分成本」，所以這裡的起點都比官方預設高一格。

價格（每百萬 token input/output）：Haiku 5.5 $0.10/$0.50（prompt 超過 100K 變 $0.50/$2.50）、Sonnet 5.5 $2/$10、Opus 5.5 $4/$20（`/fast` $8/$40）、Fable 5.1 $10/$50。

| 檔案 | 內容 | 什麼時候讀 |
|---|---|---|
| `references/effort-evidence.md` | 四模型五檔的 CursorBench 與 Artificial Analysis 表、每升一檔多拿到什麼、Opus 5.5 官方曲線、Thariq 實測 | 要不要升檔，或被問為什麼是這一檔 |
| `references/model-picks.md` | Fable 5.1 還值得選的情境、Sonnet 5.5 與 Haiku 5.5 什麼時候選（benchmark、System Card 重點） | 在模型之間猶豫，或要引數字 |
| `references/models-and-cc.md` | 模型規格速查、legacy 模型、Claude Code 現況（alias、預設、effort 控制方法與優先序、Stan 現況）、Opus 5.5 prompt 技巧 | 寫 API 整合、設定 CC、寫 prompt |
| `references/opus55-system-card.md` | Opus 5.5 System Card 摘要與使用對策、5.5 世代跨模型安全發現 | 安全、prompt injection、無人值守、代理人行為雷點 |
| `references/sources.md` | 資料來源、資料時效、未驗證項 | 引用數字前確認沒過期 |

## 分類流程

1. 對照下方決策表選出模型與 effort 起點。
2. 逐條檢查硬規則，命中就修正。
3. 按輸出格式回答，不展開長篇。
4. 跑起來不夠時照「升階路徑」，一次升一格。
5. 要數字、引句或被質疑時，才讀對應的 `references/` 檔。

## 決策表

預設答案是 **Opus 5.5 @ high**。官方原話：「Most workloads start with Claude Opus 5.5」；檔位比官方預設 medium 高一格，因為 medium 升 high 在四個來源都多 2.5 到 4.2 分。Sonnet 5.5 一律從 high 起（預設 medium 是它最弱的實用檔）；Haiku 5.5 只接輸出可以逐條檢查的量產活；Fable 5.1 只當 Opus 卡關後的一格。

| 任務類型 | 模型 @ effort | 依據 |
|---|---|---|
| 一般開發、問答、需要判斷的實作（主 session、executor） | Opus 5.5 @ high | CursorBench medium 52.5 → high 56.0、AA 51 → 54、SWE-bench Pro +2.5；代價是 token 約多 36%、首字 28s → 57s |
| 你逐次看結果的快速來回、讀圖表 | Opus 5.5 @ medium；要更快加 `/fast` | 人在迴圈裡，速度比最後幾分重要；官方：low 讀密集圖表已比 Opus 5 max 準 |
| 修既有 bug、邊界多、executor 漏過邊界 | Opus 5.5 @ xhigh（executor-high） | high → xhigh：AA +2、SWE-bench Pro +1.4；派出去沒人等著，慢沒關係 |
| 安全（auth、秘鑰、驗證、加密、漏洞） | Opus 5.5 @ xhigh（security-executor）；**不用 Fable 起手** | 資安是最吃 effort 的領域（Thariq：Security 64 → 87%）；Fable 的例外見硬規則 1 |
| 30 分鐘以上無人值守、長交付物（稽核、遷移、完整分析文件） | Opus 5.5 @ xhigh + 反早停 prompt | AA-Briefcase high 1705 → xhigh 1780；早停接法見硬規則 8 |
| 完工複驗（verifier） | Opus 5.5 @ high | Thariq：「Verify and test on high effort」；不升 xhigh，完工檢查不要更慢；Opus 自評偏誤最小 |
| 查找盤點（scout）、規格寫死的機械活（mech-executor） | Sonnet 5.5 @ high | Sonnet medium → high：CursorBench +8.6，是它最大的一跳；成本仍只有 Opus medium 的 41% 到 66% |
| 大量平行 fan-out：coding、審查 | `model: "sonnet"` + `effort: "xhigh"` | Sonnet xhigh（CB 53.1、AA 52）約等於 Opus medium，吃 Sonnet 自己的週上限；Sonnet 的 FrontierCode 最高分在 xhigh |
| 大量平行 fan-out：抽取、分類、摘要 | `model: "haiku"` + `effort: "high"`，派工單寫明只准碰哪些路徑 | Haiku medium → high：CursorBench +5.4；high 是官方建議的嚴格照指令檔；寫明邊界後越界率 30% → 1.8% |
| 電腦操作、vision、圖表/簡報/試算表知識工作 | Opus 5.5 @ high；長交付物 xhigh | OSWorld 2.0 81.8%、GDPval-AA 1846 Elo 皆最高 |
| coding 卡關（Opus 5.5 @ xhigh 試 2 次仍同一失敗） | 回報 Stan，建議 Opus 5.5 @ max（只開當次 session） | xhigh → max：CursorBench +1.8；代價見硬規則 3 |
| 模糊根因、架構決策、Opus 修不好的弱點、研究級深推理（Opus 高檔試過仍不行） | 回報 Stan，建議 Fable 5.1 @ xhigh；長文件交付用 high | Fable high → xhigh：CursorBench +2.4、AA +2；Endor Labs 弱點修補 Fable 87.2% vs Opus 68.7% |
| 互動式 live debug 要快 | Opus 5.5 + `/fast` | 同模型同品質、輸出快 2.5x；$8/$40，訂閱方案只能走 usage credits |
| 大規模平行（稽核全 repo、遷移、多視角驗證） | ultracode 或明講「用 workflow」 | 這是編排方式不是檔位；引擎上限 16 併發 / 1000 agent |

### Fable 5.1、Sonnet 5.5、Haiku 5.5 的界線

細節、benchmark 與頁碼在 `references/model-picks.md`。

- **Fable 5.1**：Opus 5.5 卡關後才上。兩種情況：模糊的根因調查、架構決策、要一次就對的工作，Opus 5.5 @ high 與 xhigh 各試 2 次仍不行；或 Opus 修不好的弱點修補（Endor Labs 179 題，只有這一份資料、effort 沒標）。effort 用 xhigh；長交付物用 high（xhigh 會先在 thinking 打一次草稿，token 約翻倍）；max 跟 xhigh 同分，不開。CursorBench 上 Opus 5.5 從 medium 到 xhigh 每一檔都贏 Fable max。派工單加「只碰要求的範圍」「把整件事做完」兩句。中途從 Opus 5.5 升到 Fable 5.1 會保留推理，反向會丟。
- **Sonnet 5.5**：範圍清楚、有驗收方法的 coding、修 bug、文件簡報試算表、量大的派工。一律從 high 起，fan-out coding 用 xhigh；不開 low（會沒驗證就回報完成）、不開 max（FrontierCode 退步、首字 450s）。Opus 週額度緊時，規格清楚的活移到 Sonnet high。開放式長程判斷、長 context 精準檢索用 Opus 5.5。
- **Haiku 5.5**：大量抽取、分類、摘要，輸出可以逐條檢查。effort 用 high；不開 low（長 prompt 會跳過搜尋、提早停）、不開 xhigh/max（xhigh 多輪對話會空回覆，max 跟 Sonnet high 同價又慢）。prompt 維持 100K 以內。不給要判斷的實作、安全、複驗：輸入幻覺、重要遺漏、謊報完成三項都輸 Opus 5.5 與 Sonnet 5.5。scout 不換 Haiku，因為輸入幻覺正是 scout 最怕的錯。
- **要不要從 Opus 降 Sonnet**：自己量，`/claude-api build-eval` 建評測、`/claude-api hillclimb` 調 prompt（CC v2.1.259 起）。

## 升階路徑（起點不夠時）

決策表給的是起點，跑起來不夠才照這裡升，一次一格。依據：Thariq 實測（effort 多買的是驗證與邊界覆蓋）、官方「調 effort 常比換模型更好的槓桿」。停損次數與「卡關後由 Stan 決定」是 Stan 的自訂規則，不是官方數字。

```
Haiku 5.5 @ high（只限抽取、分類、摘要）
  ↓ 要判斷或要改檔
Sonnet 5.5 @ high
  ↓ 範圍清楚、只是難 → Sonnet 5.5 @ xhigh（Sonnet 最多到這）
  ↓ 要判斷、長程、越做越大 → 直接跳下一格
Opus 5.5 @ high（預設起點）
  ↓
Opus 5.5 @ xhigh
  ↓ 各試 2 次仍同一失敗 → 停下回報 Stan，附建議的下一格：
  ├ coding 卡關 → Opus 5.5 @ max（只開當次 session）
  └ 模糊根因、架構、Opus 修不好的弱點、研究級深推理 → Fable 5.1 @ xhigh（長文件交付用 high）
```

max 不當任何角色或設定的預設（硬規則 3）。

**升 effort（同模型上一格）的訊號**：effort 主要多買驗證與邊界覆蓋，看到這類失敗就升。
- 邊界情況掛掉、修 A 壞 B、測試只測正常路徑。
- 修 bug 前沒先重現、沒拿獨立方法對照驗證（Thariq 的 Opus 5.5 三個例子 0/5 → 4/5 以上，差別都在這兩件事）。
- 回報完成但 transcript 沒有測試或 build 輸出。Sonnet、Haiku 先套硬規則 13 的段落，還是跳過才升。
- 任務在最吃 effort 的領域（資安、硬體、修既有 codebase 的 bug）：起點直接 xhigh，不必等失敗。
- 高檔派工單把範圍寫死：三個模型的 FrontierCode 最高分都不在 max，檔位越高越容易改到範圍外的東西（Opus 5.5 p176）。

**升模型的訊號**：
- 同模型已到頂仍失敗：Haiku 到 high、Sonnet 到 xhigh、Opus 到 xhigh。
- 任務性質變了：本來範圍明確，做下去變成要持續判斷、跨很多檔、spec 邊做邊補。Sonnet 換 Opus（官方：開放式長程工作 Opus「clearly stronger」）。
- 要在很長的 context 裡精準找東西：ProgramBench 1M 視窗 Sonnet 5.5 79.7、Opus 5.5 91.2（p118）。
- Sonnet 5.5 @ xhigh 還是不過：換 Opus 5.5 @ high，不開 Sonnet max。

**不要升的情況**（升了沒用，甚至更糟）：
- **讀錯題、方向錯**：Fable 5.1 從 low 到 max，「選錯解讀」由 25 增加到 47。訊號是成品很完整，但回答了別的問題。改 spec、叫它先訪談你或先複述任務，再用原檔位重跑。
- **Sonnet 或 Haiku subagent 中途停下來問**：派工單規格不夠。補規格重派，不是換大模型。
- **被分類器擋**：不是能力問題，照硬規則 1。
- **環境壞了**：依賴沒裝、指令起不來、權限不足。先修環境。
- **Opus 5.5 做一半用純文字停下**：這是早停，接法在硬規則 8，升檔不會好。

**停損**（自訂）：同一格最多試 2 次。到 Opus 5.5 @ xhigh 還是同一個失敗，就停下來，把失敗樣本、試過的檔位和建議的下一格回報 Stan，由 Stan 決定開不開 max 或 Fable，不自己往上爬。

**怎麼升**：
- 主 session 臨時升降：打 `/effort`（不帶參數）開滑桿，選好按 `s`，只套這個 session。**直接打 `/effort high` 或滑桿按 Enter 會存成這個模型之後的預設**（寫進 user settings 的 `modelSettings`）；`/effort auto` 清掉存檔。Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1 換檔保 cache（硬規則 2）。
- 只想這一題想深一點：prompt 裡寫 `ultrathink`。送給 API 的 effort 不變，CC 只加一段「想深一點」的指示。
- max 只能 `/effort max` 或 `--effort max`，當次 session 有效；任何設定鍵都不收。
- 主 session 換模型：整段 context 重讀。盡量在任務交界換；中途需要時，把難的那塊切出去派 subagent。已知保留推理的方向只有 Opus 5.5 → Fable 5.1，其他方向（包含 Sonnet 5.5 → Opus 5.5）沒查到，當作會丟。
- subagent：角色的 effort 寫死在定義檔。scout、mech-executor 是 Sonnet 5.5 @ high；executor、verifier 是 Opus 5.5 @ high；executor-high、security-executor 是 Opus 5.5 @ xhigh。要更高就換角色（executor 漏邊界或修既有 bug 換 executor-high，安全題用 security-executor）。
- Agent 工具從 v2.1.292 起能帶 `effort`，蓋過定義檔、resume 也保留。只在 CLAUDE.md §2 的 fan-out 規則或 Stan 指定時帶；角色 agent 不帶。
- 環境變數 `CLAUDE_CODE_EFFORT_LEVEL` 優先權最高，會蓋掉所有定義檔與派工時帶的 effort，整套分層失效。不要設。
- `/tasks` 列出每個 subagent 實際跑的模型與 effort。
- 照階段排檔（Thariq 推薦迴圈）：先叫它訪談你補 spec，再實作，最後交 verifier（Opus 5.5 @ high）驗。這是事先排好的升階，不用等失敗。

**降階**：問題解決後，下一個新任務回到決策表起點，別整個 session 留在 xhigh 或 max。effort 隨時可降（保 cache）；模型只在任務交界降，Fable 5.1 → Opus 5.5 會丟掉切換前的推理。

## Effort 速查

數字表、頁碼與實測細節在 `references/effort-evidence.md`。

- 五檔：`low` / `medium` / `high` / `xhigh` / `max`。沒有「extrahigh」。
- **預設檔位分歧**：Opus 5.5、Sonnet 5.5、Haiku 5.5 在 Claude Code 預設 `medium`；Sonnet 5.5 **API 預設 `high`**；其他模型（Fable 5.1、Opus 5、Sonnet 5）預設 `high`。Stan 的起點比這些預設高一格（決策表）。
- **同名檔位跨模型不等值**：effort 是每個模型各自校準的。Sonnet 5.5 medium（CursorBench 39.2）遠低於 Opus 5.5 medium（52.5），Sonnet xhigh 才約等於 Opus medium；Opus 5.5 medium ≈ Opus 5 high。官方要求「重掃 effort，別沿用舊設定」。
- 是行為訊號不是硬預算，影響所有 token（thinking、tool call 數、前後言）。同一檔裡，只處理工具結果的回合可能不思考，對話越長每回合想得越少。
- `xhigh` 支援：Haiku 5.5 / Sonnet 5.5 / Opus 5.5 / Fable 5.1 / Mythos 5.1 / Fable 5 / Opus 5 / Sonnet 5 / Opus 4.8 / 4.7；Opus 4.6 / Sonnet 4.6 只有 low/medium/high/max。
- **每升一檔多拿到什麼**（品質優先的判斷依據）：
  - Opus 5.5：medium → high 值得（各來源 +2.5 到 +4.2）；high → xhigh 沒人等著就值得（AA +2、CursorBench 持平）；xhigh → max 只當 coding 卡關的升階。
  - Sonnet 5.5：medium → high（+8.6）、high → xhigh（+5.3）都值得；xhigh → max 不值得（FrontierCode -5.9、首字 450s）。
  - Haiku 5.5：medium → high 值得（+5.4）；再往上不值得。
  - Fable 5.1：high → xhigh 非長交付物值得（+2.4）；xhigh → max 不值得（+0.2）。
- 10-03 本機實測 medium 跟 high 沒差，是題目碰到天花板；外部比較難的題目一致看得到差距。
- 要它少想就降檔；在 prompt 叫 Sonnet 或 Haiku「少想一點」不可靠。
- 官方立場：「調 effort 常比換模型更好的槓桿」。
- **Thariq 經驗法則**（claude.dev「Spending your effort」2026-09-25）：low＝要快、人在迴圈；medium＝大部分日常開發；high＝驗證重要或邊界多；max＝完全自主解難題。推薦迴圈：給 spec 叫它訪談你補細節 → 實作 → high 驗證與測試。Stan 的設定整體比這個對照高一格。

## 硬規則（逐條檢查）

1. **安全/攻防/漏洞任務從 Opus 起，不用 Fable 起手**：Fable 5.1 與 Opus 5.5 分類器同級（p2、p55），換 Fable 不會比較少被擋。原始碼找漏洞允許，編譯後 binary 找漏洞一律擋；被 cyber 分類器擋下的請求在 Claude Code 自動改送 Opus 4.8（API 要開發者 opt-in，p48）。Opus 5 政策相同但沒有 Opus 5.5 那層「暫時加寬的安全邊際」，誤擋可能較少（推論，未實測），看到 refusal 或降級跡象可改 Opus 5。Sonnet 5.5 也有 cyber 分類器，被擋改送 Sonnet 5；bio 被擋直接拒絕，沒有 fallback。**例外**：Opus 5.5 @ xhigh 試 2 次修不好的弱點修補，回報 Stan 時可建議 Fable 5.1 @ xhigh（Endor Labs：功能通過率 Fable 87.2%、Opus 68.7%，單一來源、effort 沒標）。
2. **中途換檔看模型（Claude Code）**：Opus 5.5、Sonnet 5.5、Haiku 5.5 與 Fable 5.1 用 API key 或訂閱登入時，換 effort 保 cache、不跳確認（Fable 要 v2.1.260 起）；其他模型換檔整段重讀，cache 還熱時 CC 會先問。例外照樣重讀：Bedrock、Google Cloud Agent Platform、Claude apps gateway、設了 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`、HIPAA 組織。直接打 `/effort <檔位>` 或滑桿按 Enter 會存成之後 session 的預設，滑桿按 `s` 只套這個 session。換模型（含分類器自動 fallback）一定整段重讀。API 端 per-message effort beta 是 `mid-conversation-output-config-2026-07-01`。
3. **max 不當預設**：官方原話「Reserve xhigh and max for work where you've measured a quality gain」。Opus 5.5 FrontierCode 在 medium 以上下降、Terminal-Bench max 不比 xhigh 高；Sonnet 5.5 max 的 FrontierCode 比 xhigh 低 5.9；Fable 5.1 max 跟 xhigh 同分。max 只有兩種用法：coding 在 Opus 5.5 @ xhigh 卡關、Stan 同意後開當次 session；無人看管的漏洞搜尋，而且多抓到一個就值得 3 倍以上成本。另外 max 會提高照做「貼上文字裡被植入的指令」的比率（預設檔約 2%，max 約 7.4%，p126），開 max 時不要讀沒包裝的外部貼文。
4. **Opus 5.5 / Sonnet 5.5 / Haiku 5.5 在 CC 預設 medium，不是 high**：user settings 頂層的 `effortLevel` 對 Opus 5.5 及之後發佈的模型**不生效**，要在 `modelSettings["claude-opus-5-5"].effortLevel`（Sonnet 是 `"claude-sonnet-5-5"`，Haiku 是 `"claude-haiku-5-5"`）明寫，或在 session 裡直接打 `/effort high` 存（v2.1.251 起就是存到 `modelSettings`）。project/local/managed 設定裡的頂層 `effortLevel` 仍有效；`max` 兩個鍵都不收。Stan 現況（2026-10-13）：頂層 `effortLevel: "high"` 只剩 Fable 5.1 吃得到；主 session 要 high 得靠 `/effort high` 存進 `modelSettings`。
5. **ultracode 不是 effort 檔位**：是 Claude Code 設定＝送 xhigh + 自動 workflow 編排，session-only；`effortLevel` 與 `CLAUDE_CODE_EFFORT_LEVEL` 都不收 max/ultracode。
6. **xhigh/max 要配大 max_tokens**：API 端至少 64K，16K 會截斷約 25% 的 Opus 與 43% 的 Fable 嘗試；Opus 5.5 官方實測長 agentic turn 直接給 128k（模型上限）。thinking 算進 max_tokens，即使沒回傳。
7. **Opus 5.5 API 四個 breaking change**：thinking 關不掉、`tool_choice: any/tool` 回 400（改 `auto` + `strict: true`）、`computer_20251124` 在 API/GCP 回 400（改 `computer_toolset_20260801`）、thinking block 綁模型與對話（2026-08-31 後建立的帳號改動 prefix 直接 400；對話要 append-only，改指令用 mid-conversation system message）。前三條 Fable 5.1 也一樣。Sonnet 5.5 四條全中，另有：關 thinking 改送 `between_tools`（xhigh/max 下 400、開了就不能中途換 effort）、`temperature`/`top_p`/`top_k` 非預設值 400、advisor 工具不收 Opus 4.8/4.7、Sonnet 5 與 Haiku 5.5。Haiku 5.5 同樣不要送 `temperature`/`top_p`/`top_k`。
8. **無人值守長任務要接早停**：Opus 5.5 會在部分完成時用純文字 end_turn 回報，harness 把它當完工就斷了。對策：checklist 檔 + 剩餘項目 nudge（最多 2-3 次）+ system prompt 末尾點名不要的四種停法（官方有整段範本）。人在線的互動 session 不要加。
9. **tool call 之間的文字進 thinking block**：Opus 5.5 / Fable 5.1 把進度說明放 progress-update thinking block，預設 `display: "omitted"` 看起來像卡住。自寫的 API 整合要設 `display: "updates"`（`thinking-display-updates-2026-08-18`）。
10. **別叫 Opus 5.5 把推理寫進回答**：會觸發 `reasoning_extraction` refusal，且 server-side fallback 對此類不重試。要推理就開 `display: "summarized"`。Skill/prompt 裡「先寫出你的推理再回答」這種句子要拔。
11. **fast mode 是速度不是智力**：同模型同權重，只快輸出（OTPS），首 token 不快。訂閱方案走 usage credits 不算訂閱額度；開啟當下要付整段 context 的未快取 input 價，所以要開就 session 一開始開。只有一段對話第一次開 fast 會整段重讀；之後關掉、被限流自動退回標準速度、再打開都保 cache。
12. Haiku 5.5 / Sonnet 5.5 / Sonnet 5 / Fable 5.1 / Opus 5.5 都是新 tokenizer，同文字比 Opus 4.7 前（含 Haiku 4.5）約 +30% token：從舊模型搬來的 max_tokens/成本估算要重算（Sonnet 5 → 5.5 同 tokenizer，不用重算）。
13. **Sonnet 5.5 與 Haiku 5.5 要逼它驗證**：官方承認 Sonnet low 有時沒跑能驗到改動的檢查就回報完成（例如依賴沒裝就跳過測試），low/medium 長任務會停下來問本來可以自己決定的事；Haiku medium 以下會跳過驗證，謊報完成也比 Opus、Sonnet 多。對策：派工單或 system prompt 貼官方那段「改了能跑的程式就先跑真的測試、型別檢查或 build 再回報；跑不了就說哪個沒跑、為什麼」，要它做完再停就加官方「Keep working until everything the user asked for is done…」段。
14. **Haiku 5.5 的位置**（2026-10-13 解禁，規格已查證）：$0.10/$0.50（prompt 超過 100K 變 $0.50/$2.50）、cache read $0.01、1M context、CC 預設 medium、五檔都支援；`haiku` 別名 v2.1.293 起指向它。只接大量抽取、分類、摘要，effort 開 high；派工單加一段工作邊界說明（只准碰哪些路徑、不准做什麼），System Card 實測越界率從 30% 降到 1.8%。要判斷的實作、安全、複驗、scout 不給它。Haiku 4.5 不再使用。
15. **fan-out 一律帶 model 也帶 effort**：照 CLAUDE.md §2，coding、審查帶 `model: "sonnet"` + `effort: "xhigh"`，抽取、分類帶 `model: "haiku"` + `effort: "high"`。沒帶 effort 時 subagent 大概跟 session 走（文件只暗示，沒明講），結果不可預期。

## 輸出格式

```
模型：<X>（備援：<Y>）
Effort：<檔位>
理由：<一行，引用上表依據>
雷點：<命中的硬規則，無則省略>
下一格：<不夠時往哪升、看到什麼訊號才升；已到頂就寫停損>
```

## 常見錯誤

| 錯誤 | 正解 |
|---|---|
| 「最強任務→Fable」反射 | CursorBench 上 Opus 5.5 從 medium 到 xhigh 每一檔都贏 Fable max，成本 1/6 到 2/5；Fable 只在 Opus 高檔卡關後、經 Stan 同意 |
| 主 session 留在 Opus 5.5 預設 medium | Stan 品質優先，主 session 與 executor 開 high；medium 留給你逐次看結果的快速來回 |
| 沿用舊 `effortLevel: high` 以為 Opus 5.5 也在 high | Opus 5.5 不吃頂層 effortLevel，要 `/effort high` 或 `modelSettings` 明寫 |
| 以為打 `/effort high` 只套這個 session | 直接打會存成預設；只套這個 session 要開滑桿按 `s` |
| 設 `CLAUDE_CODE_EFFORT_LEVEL` 想一次調高全部 | 它蓋掉所有 agent 定義與派工時的 effort，角色分層全部失效 |
| 把 ultracode 當第六檔 | 它是編排設定；最深推理照升階路徑，max 要 Stan 同意 |
| 安全稽核選 Fable「因為最聰明」 | 硬規則 1：從 Opus 5.5 @ xhigh 起；Fable 只接 Opus 修不好的弱點 |
| 在 Sonnet 5 / Opus 5 對話中途換檔 | 這些模型換檔整段重讀；Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1 才保 cache |
| 以為 Sonnet 5.5 只有低檔才省錢 | 反過來：high 才是 Sonnet 最划算的一檔（Opus medium 成本的 41% 到 66%）；xhigh 約等於 Opus medium 同分同價 |
| Sonnet 5.5 留在預設 medium，或派 `model: "sonnet"` 不帶 effort | medium 是 Sonnet 最弱的實用檔（CursorBench 39.2，high 47.8）；角色定義已寫 high，fan-out 照硬規則 15 帶 xhigh |
| Sonnet 5.5 開 max 求穩 | FrontierCode max 46.2 反而低於 xhigh 52.1：max 會自己開 review 輪、拆 subagent，逾時或越界 |
| Sonnet 或 Haiku 回報「完成」就收 | 低檔可能沒跑測試；看 transcript 有沒有測試或 build 輸出，沒有就套硬規則 13 的官方段落 |
| 要判斷的活派 Haiku 5.5、Haiku 開 low 或 xhigh、還在用 Haiku 4.5 | Haiku 5.5 只接抽取、分類、摘要，開 high（硬規則 14） |
| 失敗就一路往上加到 max 或 Fable | 照升階路徑一次一格、每格最多兩次；到 Opus 5.5 @ xhigh 還失敗就停下回報 Stan，附建議下一格 |
| 派角色 agent 時另外帶 effort | 角色的 effort 寫死在定義檔；Agent 工具的 effort 只在 CLAUDE.md §2 fan-out 規則或 Stan 指定時帶 |
| 以為開 max 能修掉方向錯誤 | 高 effort 減少漏邊界，不修正讀錯題：Fable 5.1 low→max「選錯解讀」25→47 反而變多。方向問題靠訪談與 spec |
| 開 `/fast` 想省額度 | 反向：fast 走 usage credits 真金白銀，且中途開要付整段 context |
| 從 Fable 5.1 降回 Opus 5.5 想省錢 | 切換後推理全丟；要降就在新任務起點降，別在對話中間 |
| 把別人寫的 log/README/email 直接貼進 prompt | Opus 5.5 容易把 user turn 裡的字都當你的指令；包 `<pasted_content>` 並註明來源，別開 max |

## 資料時效

來源、每次更新的紀錄與未驗證項在 `references/sources.md`。逐檔分數全靠 CursorBench 與 Artificial Analysis（Anthropic 沒用文字公布 Sonnet 5.5、Haiku 5.5 的逐檔分數）；新模型發佈或 CC 大改版時，先查 platform.claude.com/docs 的 models overview 與 effort 頁、code.claude.com 的 model-config，數字過期就別引用。
