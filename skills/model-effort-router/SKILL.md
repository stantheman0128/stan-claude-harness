---
name: model-effort-router
description: Use when 需要決定一個任務該用哪個 Claude 模型與哪個 effort 檔位，或被問「用哪個模型」「opus 還是 sonnet 還是 fable」「opus 5.5 還是 fable」「sonnet 5.5 還是 opus 5.5」「effort 設多少」「什麼時候升 effort」「跑不好要不要換大模型」「subagent 用什麼檔」「ultracode 是什麼」「fast mode 要不要開」「這樣跑會不會太貴」時。也用於審視既有的模型/effort 選擇是否踩雷（安全稽核用錯模型、對話中途換檔、max 濫用、Opus 5.5 預設 medium 沒調）。純分類與建議，不執行任務本身。
---

# Model / Effort Router

## Overview

任務分類器：輸入任務描述，輸出「模型 + effort + 一行理由 + 雷點 + 下一格」。本檔只放做決定要用的規則；數據、引句、頁碼與 API 細節放在 `references/`，被質疑、要引數字或寫 API 整合時才讀。資料截至 2026-10-03。

價格（每百萬 token input/output）：Sonnet 5.5 $2/$10、Opus 5.5 $4/$20（`/fast` $8/$40）、Fable 5.1 $10/$50。

| 檔案 | 內容 | 什麼時候讀 |
|---|---|---|
| `references/model-picks.md` | Fable 5.1 還值得選的情境、Sonnet 5.5 什麼時候選（benchmark 表、Sonnet 5.5 System Card 重點） | 在 Opus / Sonnet / Fable 之間猶豫，或要引數字 |
| `references/effort-evidence.md` | Opus 5 / Opus 5.5 effort 曲線、Thariq 實測細節 | 要不要上 xhigh/max，或解釋為什麼升、不升 |
| `references/models-and-cc.md` | 模型特性速查表、legacy 模型、Claude Code 現況（alias、預設、effort 解析順序）、Opus 5.5 prompt 技巧 | 寫 API 整合、設定 CC、寫 prompt |
| `references/opus55-system-card.md` | Opus 5.5 System Card 摘要與使用對策 | 安全、prompt injection、無人值守、代理人行為雷點 |
| `references/sources.md` | 資料來源、資料時效、未驗證項 | 引用數字前確認沒過期 |

## 分類流程

1. 對照下方決策表選出模型與 effort 起點。
2. 逐條檢查硬規則，命中就修正。
3. 按輸出格式回答，不展開長篇。
4. 跑起來不夠時照「升階路徑」，一次升一格。
5. 要數字、引句或被質疑時，才讀對應的 `references/` 檔。

## 決策表

預設答案是 **Opus 5.5**。官方原話：「Most workloads start with Claude Opus 5.5」；Fable 5.1 留給「Opus 5.5 開到 xhigh/max 評測仍不夠」的深推理與長程 agent 任務；Sonnet 5.5 接範圍明確、有辦法驗收的日常工作（見下方「Fable 5.1 與 Sonnet 5.5 的界線」）。

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

### Fable 5.1 與 Sonnet 5.5 的界線

細節、benchmark 與頁碼在 `references/model-picks.md`。

- **Fable 5.1**：只給 Opus 5.5 @ xhigh 量過仍不夠的深推理、研究級數學、數小時單一 agent。System Card 裡沒有任何 coding/agentic benchmark 是 Fable 贏的；安全題不用（分類器同級）；網傳「架構、洞見比較強」兩份 card 都沒數據支持。中途從 Opus 5.5 升到 Fable 5.1 會保留推理，反向會丟。
- **Sonnet 5.5**：有清楚 spec 和驗收方法、修既有 bug、產文件簡報試算表、量大的派工時選它。省錢只在 low/medium，high 以上花費接近 Opus 5.5；max 通常比 xhigh 差；開放式長程判斷、長 context 精準檢索用 Opus 5.5。
- **要不要從 Opus 降 Sonnet**：自己量，`/claude-api build-eval` 建評測、`/claude-api hillclimb` 調 prompt（CC v2.1.259 起）。

## 升階路徑（起點不夠時）

決策表給的是起點，跑起來不夠才照這裡升，一次一格。依據：Thariq 實測（effort 多買的是驗證與邊界覆蓋）、官方「調 effort 常比換模型更好的槓桿」、Sonnet 5.5 高檔花費接近 Opus 5.5、Fable 只在 Opus 5.5 高檔評測仍不夠時才上。停損次數是 Stan 的自訂規則，不是官方數字。

```
Sonnet 5.5 @ low
  ↓
Sonnet 5.5 @ medium
  ↓ 範圍明確、只是難 → Sonnet 5.5 @ high（Sonnet 最多到這）
  ↓ 要判斷、長程、越做越大 → 直接跳下一格
Opus 5.5 @ medium
  ↓
Opus 5.5 @ high
  ↓
Opus 5.5 @ xhigh
  ↓ 只限深推理、研究級數學、數小時單一 agent，且 xhigh 量過仍不夠；安全題不走這格
Fable 5.1 @ high
```

max 不在梯子上，量到增益才用（硬規則 3）。

**升 effort（同模型上一格）的訊號**：effort 主要多買驗證與邊界覆蓋，看到這類失敗就升。
- 邊界情況掛掉、修 A 壞 B、測試只測正常路徑。
- 修 bug 前沒先重現、沒拿獨立方法對照驗證（Thariq 的 Opus 5.5 三個例子 0/5 → 4/5 以上，差別都在這兩件事）。
- 回報完成但 transcript 沒有測試或 build 輸出。Sonnet 5.5 @ low 先套硬規則 13 的段落，還是跳過才升 medium。
- 任務在最吃 effort 的領域（資安、硬體、修既有 codebase 的 bug）：起點直接 high，不必等失敗。
- coding 從 Opus 5.5 medium 升 high 時，派工單把範圍寫死：FrontierCode 在 medium 以上下降，原因是高檔會改到範圍外（p176）。

**升模型的訊號**：
- 同模型已到頂仍失敗：Sonnet 5.5 到 high、Opus 5.5 到 xhigh。
- 任務性質變了：本來範圍明確，做下去變成要持續判斷、跨很多檔、spec 邊做邊補。Sonnet 換 Opus（官方：開放式長程工作 Opus「clearly stronger」）。
- 要在很長的 context 裡精準找東西：ProgramBench 1M 視窗 Sonnet 5.5 79.7、Opus 5.5 91.2（p118）。
- Sonnet 5.5 要開 xhigh/max 才過：直接 Opus 5.5 @ medium，CursorBench 上分數較高也較便宜（數字見 `references/model-picks.md` 的 Sonnet 5.5 System Card 重點）。

**不要升的情況**（升了沒用，甚至更糟）：
- **讀錯題、方向錯**：Fable 5.1 從 low 到 max，「選錯解讀」由 25 增加到 47。訊號是成品很完整，但回答了別的問題。改 spec、叫它先訪談你或先複述任務，再用原檔位重跑。
- **被分類器擋**：不是能力問題，照硬規則 1。
- **環境壞了**：依賴沒裝、指令起不來、權限不足。先修環境。
- **Opus 5.5 做一半用純文字停下**：這是早停，接法在硬規則 8，升檔不會好。

**停損**（自訂）：同一格最多試 2 次。到 Opus 5.5 @ xhigh 還是同一個失敗，就停下來，把失敗樣本和試過的檔位回報 Stan，不自己往 Fable 或 max 爬。

**怎麼升**：
- 主 session 升 effort：`/effort high` 後按 `s` 只套這個 session，按 Enter 會存成之後的預設。Opus 5.5 / Sonnet 5.5 / Fable 5.1 換檔保 cache（硬規則 2）。
- 主 session 換模型：整段 context 重讀。盡量在任務交界換；中途需要時，把難的那塊切出去派 subagent。已知保留推理的方向只有 Opus 5.5 → Fable 5.1，其他方向（包含 Sonnet 5.5 → Opus 5.5）沒查到，當作會丟。
- subagent：Agent 工具能指定 model、不能指定 effort，所以升 effort 就是換角色 agent。scout、mech-executor 是 Sonnet 5.5 @ low；executor 是 Opus 5.5 @ medium；executor-high、security-executor、verifier 是 Opus 5.5 @ high。executor 漏邊界或修既有 bug 就換 executor-high，安全題用 security-executor。Opus 5.5 @ xhigh 沒有對應角色，在主 session 做。
- 照階段排檔（Thariq 推薦迴圈）：先叫它訪談你補 spec，再用 low 或 medium 實作，最後交 verifier（Opus 5.5 @ high）驗。這是事先排好的升階，不用等失敗。

**降階**：問題解決後，下一個新任務回到決策表起點，別整個 session 留在高檔。effort 隨時可降（保 cache）；模型只在任務交界降，Fable 5.1 → Opus 5.5 會丟掉切換前的推理。

## Effort 速查

曲線、頁碼與實測細節在 `references/effort-evidence.md`。

- 五檔：`low` / `medium` / `high` / `xhigh` / `max`。沒有「extrahigh」。
- **預設檔位分歧**：Opus 5.5 預設 `medium`（API 與 Claude Code）；Sonnet 5.5 在 Claude Code 與 app 預設 `medium`，**API 預設 `high`**；其他模型（Fable 5.1、Opus 5、Sonnet 5）預設 `high`。
- **Sonnet 5.5 起點**（官方）：agentic coding 與多步 tool use，規格明確從 `medium` 起，難或長的上 `high`；聊天類從 `medium` 或 `low`。檔位重新校準過，同名檔位的思考量跟 Sonnet 5 不一樣，別沿用舊設定。在 system prompt 叫它「少想一點」不可靠，要少想就降檔。
- 是行為訊號不是硬預算，影響所有 token（thinking、tool call 數、前後言）。
- `xhigh`：Fable 5.1 / Mythos 5.1 / Fable 5 / Opus 5.5 / Opus 5 / Opus 4.8 / 4.7 / Sonnet 5.5 / Sonnet 5；Opus 4.6 / Sonnet 4.6 只有 low/medium/high/max。
- 檔位名跨模型不等值：Opus 5.5 medium ≈ Opus 5 high；同檔位 Opus 5.5 思考量 > Opus 5，xhigh/max 差最多。官方要求「重掃 effort，別沿用舊設定」。
- **結論**：coding 給 medium~high，只有明確要更多推理的評測才上 xhigh，max 幾乎沒有理由（Opus 5.5 FrontierCode 在 medium 最高，p176）。
- 官方立場：「調 effort 常比換模型更好的槓桿」。
- **Thariq 經驗法則**（claude.dev「Spending your effort」2026-09-25）：
  - 經驗法則：low＝要快、人在迴圈（腦力激盪、草稿、簡單修改）；medium＝大部分日常開發與新功能；high＝驗證重要或邊界多（修既有 codebase 的 bug）；max＝完全自主解難題（端到端建 app 並驗證、關鍵軟體找漏洞）。
  - 推薦迴圈：給 spec 叫它訪談你補細節 → low 實作與迭代 → high 驗證與測試。

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
14. **不路由到 Haiku**（Stan 2026-10-02：「現在 haiku 超級爛」）：最便宜的一格是 Sonnet 5.5 @ low。Haiku 4.5 不支援 effort、只有 200K context、退役日不早於 2026-10-15。agent 定義、Workflow `agent()`、派工時的 `model` 參數都不寫 haiku；ocx-* agent 說明裡的 `"haiku"` 佔位符直接省略。Haiku 5.5 發佈後要 Stan 點頭才解禁。

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
| 「最強任務→Fable」反射 | Opus 5.5 九項官方 benchmark 全部領先或持平、價格 40%；Fable 只在 Opus 5.5 高檔評測仍不夠時 |
| 「Opus 5 @ xhigh 是難 coding 起點」 | 那是 Opus 5 時代；Opus 5.5 從 medium 起，medium 已 ≥ Opus 5 high |
| 沿用舊 `effortLevel: high` 以為 Opus 5.5 也在 high | Opus 5.5 不吃頂層 effortLevel，要 `modelSettings` 明寫 |
| 把 ultracode 當第六檔 | 它是編排設定；最深推理設 max（先測） |
| 安全稽核選 Fable「因為最聰明」 | 硬規則 1：分類器同級，白付錢 |
| 在 Sonnet 5 / Opus 5 對話中途換檔 | 這些模型換檔整段重讀；Opus 5.5 / Sonnet 5.5 / Fable 5.1 才保 cache，可以照工作階段換檔 |
| 把 Sonnet 5.5 開 high/xhigh 當便宜版 Opus | 高檔 Sonnet 5.5 的花費跟 Opus 5.5 差不多；省錢只在 low/medium。xhigh/max 才過的任務官方叫你考慮 Opus 5.5 |
| Sonnet 5.5 開 max 求穩 | FrontierCode max 46.2 反而低於 xhigh 52.1：max 會自己開 review 輪、拆 subagent，逾時或越界 |
| Sonnet 5.5 @ low 回報「完成」就收 | low 可能沒跑測試；看 transcript 有沒有測試或 build 輸出，沒有就套硬規則 13 的官方段落 |
| 便宜的活派 Haiku | 最低一格是 Sonnet 5.5 @ low（硬規則 14） |
| 失敗就一路往上加到 max 或 Fable | 照升階路徑一次一格、每格最多兩次；到 Opus 5.5 @ xhigh 還失敗就停下回報 |
| 派 subagent 時想在 Agent 工具指定 effort | 只能指定 model；要不同 effort 就換角色 agent |
| 以為開 max 能修掉方向錯誤 | 高 effort 減少漏邊界，不修正讀錯題：Fable 5.1 low→max「選錯解讀」25→47 反而變多。方向問題靠訪談與 spec |
| 開 `/fast` 想省額度 | 反向：fast 走 usage credits 真金白銀，且中途開要付整段 context |
| 從 Fable 5.1 降回 Opus 5.5 想省錢 | 切換後推理全丟；要降就在新任務起點降，別在對話中間 |
| 把別人寫的 log/README/email 直接貼進 prompt | Opus 5.5 容易把 user turn 裡的字都當你的指令；包 `<pasted_content>` 並註明來源，別開 max |

## 資料時效

來源、每次更新的紀錄與未驗證項在 `references/sources.md`。Haiku 5.5 發佈後，先查 platform.claude.com/docs 的 models overview 與 effort 頁再回答，數字過期就別引用。
