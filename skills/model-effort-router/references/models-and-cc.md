# 模型規格、Claude Code 現況與 prompt 技巧

寫 API 整合、設定 Claude Code、查 alias 與預設值時讀這份。

## 模型特性速查

| | Sonnet 5.5（$2/$10） | Opus 5.5（$4/$20） | Fable 5.2（$8/$40） |
|---|---|---|---|
| model ID | `claude-sonnet-5-5` | `claude-opus-5-5` | `claude-fable-5-2`（2026-11-09 發佈） |
| 定位 | 範圍明確的日常 coding、修 bug、文件；high 最划算 | 預設起點；agentic coding / 知識工作 / 電腦操作 | 所有客戶能用的最強模型；Opus 5.5 高檔仍不夠時 |
| cutoff | 2026-06 | 2026-06 | 2026-06 |
| context / max output | 1M / 128k（Batch beta 300k） | 1M / 128k | 1M / 128k |
| cache read | $0.10（base 5%，2026-10-07 起減半） | $0.20（base 5%） | $0.20（base 2.5%）；cache write 5 分鐘 $10、1 小時 $16 |
| batch | 未查 | $2/$10 | $4/$20 |
| API 預設 effort | high | medium | high |
| CC 預設 effort | medium | medium | medium |
| thinking | 永遠開；API 送 `disabled` 回 400，最低設定改 `between_tools`（只配 low~high）；CC 關不掉 | 永遠開、關不掉（`disabled`/`budget_tokens` 都 400） | adaptive、永遠開；`disabled` 與 `enabled`+`budget_tokens` 都 400 |
| 分類器 | 第一個帶 cyber 分類器的 Sonnet：cyber、frontier_llm 擋下改送 Sonnet 5；bio、reasoning_extraction、general_harms 無 fallback | cyber（擋下改送 Opus 4.8）、bio（擋下改送 Opus 5）、frontier_llm（改送 Opus 5）、reasoning_extraction（無 fallback） | cyber 政策同 Opus 5.5，擋下改送 Opus 4.8；bio 改送 Opus 5；早期測試比 Fable 5.1 少擋約 55% |
| prompt 脾氣 | 沿用 Sonnet 5 prompt 即可；low 可能沒跑測試就回報完成；low/medium 長任務會中途停下來問；各檔都愛順手加測試與文件；xhigh/max 會自己開 review 輪與 subagent；偶爾 tool 名大小寫打錯 | 出手快、回報清楚；長程任務會用純文字回報而早停；前端沒指示會套「AI 通用款」 | 長任務會提早結束回合（low、medium 較常）；把推論講成事實；說它「擁有 codebase」會大改；防護見 `fable52-system-card.md` |
| fast mode | 無 | `/fast`，$8/$40 | 有，$16/$80；CC 要在 Fable 5.2 上打 `/fast` 開（見下） |
| 資料保留 | | | 要 30 天資料保留，沒有 ZDR（Anthropic 明確授權除外，否則回 400） |

出處：https://platform.claude.com/docs/en/models/fable-5-2/overview 、whats-new-fable-5-2、about-claude/pricing（2026-11-14 讀）；發佈文 https://www.anthropic.com/news/claude-fable-and-mythos-5-2 。Fable 5.2 的 Bedrock ID 是 `global.anthropic.claude-fable-5-2`，退役不早於 2027-11-09。

**Mythos 5.2**（`claude-mythos-5-2`）：跟 Fable 5.2 同規格同價，只開給通過驗證計畫的組織（例如 CVP），放寬資安與生科 safeguards（reduced classifiers 仍在）。Stan 帳號 2026-11-23 實測可用（`claude -p --model claude-mythos-5-2` 有回答，usage 顯示 `claude-mythos-5-2`）；走哪個週額度桶查不到。Mythos fast mode 只開給驗證計畫內的組織。

**Legacy Fable 5.1 / Mythos 5.1**：`claude-fable-5-1`、`claude-mythos-5-1` 仍是 Active，10/50 美元、cache read $0.25，Fable 5.1 退役不早於 2027-09-01。CC 預設 effort high，user settings 頂層 `effortLevel` 對它仍有效。Fable 5.1 讀不懂 Fable 5.2 的 thinking block。

Haiku 5.5（$0.10/$0.50，prompt 超過 100K 變 $0.50/$2.50；1M context；預設 medium）的完整規格在 `model-picks.md`「Haiku 5.5 什麼時候選」。

Sonnet 5 列為 legacy 但仍 Active（退役不早於 2027-06-30）、$2/$10 定價永久維持、cutoff 2026-01、預設 high、thinking 可關、無分類器；它是 Sonnet 5.5 cyber refusal 的 fallback 目標。

Opus 5 降為 legacy（$5/$25、預設 high、thinking 可關到 high、fast mode $10/$50），仍可用；分類器較 Opus 5.5 寬鬆，是 bio/frontier_llm 類 refusal 的官方 fallback 目標。

## 換模型會不會丟推理（preserved thinking）

出處 https://platform.claude.com/docs/en/build-with-claude/preserved-thinking 與 whats-new-fable-5-2（2026-11-14 讀）。

- Fable 5.2 與 Mythos 5.2 的 thinking block 只有 Fable 5.2 與 Mythos 5.2 讀得懂；Fable 5.1、Mythos 5.1、Opus 5.5、Sonnet 5.5、Haiku 5.5 都讀不懂。從 Fable 5.2 換到任何其他模型，在那邊跑的回合會失去 Fable 5.2 的推理。
- API 上 Fable 5.2 讀得懂 Fable 5.1 與 Opus 5.5 的 block（whats-new 頁），所以 API 端 Opus 5.5 → Fable 5.2 會保留推理。Claude Code 裡換過去是否同樣保留，文件沒寫，當作未驗證。
- Opus 5.5 與 Fable 5.1 的 block，Sonnet 5.5 與 Haiku 5.5 讀不懂。
- 讀不懂的 block 不會報錯，API 這次請求直接丟掉、不計費。推理只有在自己的程式把它刪掉時才永久消失：保留完整歷史，不要每個模型各留一份。
- thinking block 綁產生它的帳號；改動 system、tools 或前面的訊息會讓 prefix 檢查失敗，Fable 5.2 與 Mythos 5.2 直接回 400。

## Claude Code 現況（2026-11-23 補到 v2.1.321）

- 預設模型：Pro/Max/Team/Enterprise/API 全部 Opus 5.5；Sonnet 5.5 不是任何方案的預設。`opus` alias → Opus 5.5；`sonnet` → Sonnet 5.5（v2.1.284 起，只限 Anthropic API；Bedrock/Agent Platform/Foundry 仍指向 Sonnet 4.5）；`opusplan` → Opus 5.5 規劃 + `sonnet` 執行（Anthropic API 上即 Sonnet 5.5，由兩句文件推得）。規劃與執行之間切換算換模型，cache 會重讀。
- **`fable` alias → Fable 5.2**（v2.1.321 起，除了 Claude apps gateway session，且沒設 `ANTHROPIC_DEFAULT_FABLE_MODEL`；gateway 要打 `/model claude-fable-5-2`）。Fable 5.2 需要 v2.1.321 起。**遷移**：v2.1.321 把存起來的 Fable 5.1 選擇改成 `fable` alias，Pro 與 Max 立刻改，Team 與 Enterprise 等組織允許；user settings 裡存的 `claude-fable-5-1` 在 Pro、Max、Ultra、Team、Enterprise 會改成 `fable`，Console 帳號與第三方平台保留 `claude-fable-5-1`。要用回 5.1 打 `/model claude-fable-5-1`（https://code.claude.com/docs/en/changelog 、model-config，2026-11-14 讀）。
- Sonnet 5.5 需要 CC v2.1.284 起；固定 1M context，沒有 200K 版、不用 usage credits，約 967K 自動 compact。
- effort 解析順序（主 session，model-config 文件）：`CLAUDE_CODE_EFFORT_LEVEL` ＞ session 裡選的檔位 ＞ `--effort` ＞ 存檔設定（`modelSettings` 逐模型，或頂層 `effortLevel`）＞ 模型預設。**CC 模型預設**：Fable 5.2、Opus 5.5、Sonnet 5.5、Haiku 5.5 是 medium；Opus 4.7 是 xhigh；其他模型 high。
- **頂層 `effortLevel`**：文件寫它對 Opus 5、Fable 5.1 與更早的模型仍有效，Opus 5.5 不吃、從 medium 起。這段沒點名 Fable 5.2，所以 Fable 5.2 吃不吃頂層 `effortLevel` 查不到。`effortLevel` 收 low、medium、high、xhigh，`max` 兩個鍵都不收，ultracode 有自己的鍵。
- **Fable 5.2 要跑 high**：切到 Fable 5.2 後打 `/effort high`（或開 `/effort` 滑桿按 Enter），會存到 `modelSettings["claude-fable-5-2"]`；只想這個 session 用就開滑桿按 `s`。CC 預設是 medium，不設就跑 medium。
- effort 解析順序（subagent）：`CLAUDE_CODE_EFFORT_LEVEL` ＞ Agent 工具派工時帶的 `effort`（v2.1.292 起，resume 也保留）＞ 定義檔 frontmatter 的 `effort:` ＞ 都沒寫時：v2.1.317 起，跟主 session 不同模型的 subagent 與 teammate 用該模型的存檔檔位或模型預設，不再用 session 的檔位；同模型時沒查到明文。v2.1.316 新增環境變數 `CLAUDE_CODE_SUBAGENT_EFFORT`，作用與優先順序沒讀到（兩條都只讀到 changelog 摘要，https://code.claude.com/docs/en/changelog ，2026-11-14 讀）。skill frontmatter 的 `effort:` 在該 skill 執行時生效，同樣蓋不過環境變數。`maxEffortLevel` 對以上全部設上限。
- `/effort` 的存與不存：不帶參數開滑桿（v2.1.257 起），按 `s` 只套這個 session、按 Enter 存；直接打 `/effort high` 也會存。存的位置是 user settings 的 `modelSettings`，每個模型各一份；`/effort auto` 清掉這個模型的存檔；`/effort status` 印出目前檔位。`/model` 選模型時按左右鍵調 effort，Enter 存、`s` 不存。`--effort` 只管這次啟動。`max` 只能當次 session，`modelSettings` 只收 low 到 xhigh。
- 換 effort 的 cache：model-config 文件沒寫換 effort 或換模型會不會保 cache，只連到 prompt-caching 文件（沒抓）。Fable 5.2 在 CC 中途換 effort 是否保 cache 未驗證。v2.1.312 修了 `/model` 與 `/effort` 的 cache 警告文字。
- 自動 fallback 時，被標記那則請求的 effort 會帶到 fallback 模型。
- `ultrathink` 寫在 prompt 裡：v2.1.311 起在互動終端機，Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1 走 Anthropic API 時這一回合改跑 xhigh（changelog 摘要，Fable 5.2 沒點名）；其他情況照 model-config 文件，只加一段想深一點的指示，送給 API 的 effort 不變。`/tasks` 列出每個 subagent 實際的模型與 effort。
- Stan 現況（2026-10-13 查 `~/.claude/settings.json`）：頂層 `effortLevel: "high"`、沒有 `modelSettings`、沒設 `CLAUDE_CODE_EFFORT_LEVEL`。2026-10-14 更新：桌面版打 `/effort high` 沒存檔，已手動寫入 `modelSettings["claude-opus-5-5"].effortLevel: "high"`（commit `5d2c28a`）；另有 `switchModelsOnFlag: false`（CLI 設定說明：訊息被 safeguard 標記時 session 暫停，不自動換模型），所以 Stan 的 CC 不會自動 fallback 到 Opus 4.8。頂層 `effortLevel: "high"` 確定只有 Fable 5.1 吃得到；Fable 5.2 吃不吃查不到，要 high 就在 Fable 5.2 上打 `/effort high`。2026-11-23 沒有再查 settings 檔。
- 不支援的檔位自動退到該模型最高可用檔（xhigh 在 Opus 4.6 跑成 high）。
- **fast mode**：`/fast` 預設模型 Opus 5.5；目前模型不支援 fast 時會自動切到 Opus。Fable 5.2 的 fast mode 只有 `fastMode` 設定沒用，要在用 Fable 5.2 時打 `/fast` 打開（v2.1.321 起）；切到 Fable 5.2 時，除非是在 Fable 5.2 上開的，fast mode 會關掉。價格 Fable 5.2 16/80、Opus 5.5 8/40、Opus 5 與 Opus 4.8 10/50 美元（https://code.claude.com/docs/en/fast-mode ，2026-11-14 讀）。同一頁也寫 fast 與標準速度各用一份 cache，之後每次切換都會重讀部分或全部對話，跟 SKILL.md 硬規則 11「之後切換都保 cache」的舊說法不一致，見 `sources.md` 未驗證項。
- Haiku 5.5（model ID `claude-haiku-5-5`，2026-10-07 發佈）v2.1.293 起是 Anthropic API 上的預設 Haiku，`haiku` 別名指向它；1M context、$0.10/$0.50（prompt 超過 100K 變 $0.50/$2.50）、五檔 effort、預設 medium。Haiku 4.5（$1/$5、200K、不支援 effort）退役日不早於 2026-10-15，不再使用。Stan 2026-10-13 解禁 Haiku 5.5（硬規則 14）。
- `/checkup prompt-audit [路徑]`（v2.1.283 起，`/doctor` 的別名）：掃 CLAUDE.md、rules、skills、commands、subagents、output styles，找過時路徑、互相矛盾、「CRITICAL/MUST」施壓語氣、「think harder」這類對永遠開 thinking 的模型無效的句子、寫死的模型名。只提案不改檔；不讀 settings/hooks/MCP 設定。兩份官方文件對預設是否掃 `~/.claude/` 說法不一，路徑要自己給。

## API breaking change 與換檔 cache 例外（2026-11-23 從 SKILL.md 硬規則 2、7 移來）

- **API breaking change**：Opus 5.5 四條：thinking 關不掉、`tool_choice: any/tool` 回 400（改 `auto` + `strict: true`）、`computer_20251124` 在 API/GCP 回 400（改 `computer_toolset_20260801`）、thinking block 綁模型與對話（2026-08-31 後建立的帳號改動 prefix 直接 400；對話要 append-only，改指令用 mid-conversation system message）。前三條 Fable 5.1 也一樣。**Fable 5.2 / Mythos 5.2**：prefix 檢查失敗 400；它的 thinking block 只有 5.2 家族讀得懂；`computer_20251124` 除 Bedrock 外 400；executor 的 advisor 只能是 Fable 5.2 或 Mythos 5.2；強制 tool use 400；`temperature`/`top_p`/`top_k` 在 API 版本 2026-10-21 移除，送了 400；要 30 天資料保留、沒有 ZDR。Sonnet 5.5 四條全中，另有：關 thinking 改送 `between_tools`（xhigh/max 下 400、開了就不能中途換 effort）、`temperature`/`top_p`/`top_k` 非預設值 400、advisor 工具不收 Opus 4.8/4.7、Sonnet 5 與 Haiku 5.5。Haiku 5.5 同樣不要送 `temperature`/`top_p`/`top_k`。
- **換 effort 保 cache 的例外**（CC 裡 Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1 平常保 cache）：例外照樣重讀：Bedrock、Google Cloud Agent Platform、Claude apps gateway、設了 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`、HIPAA 組織。
- API 端 per-message effort（beta `mid-conversation-output-config-2026-07-01`）支援 Fable 5.2 與 Mythos 5.2，會保 cache；改頂層 effort 會讓 cache 部分或全部失效。

## Advisor 搭配（含未採用的提案）

**未採用：主 session Opus 5.5 配 Fable 5.2 advisor**（2026-11-23 Stan 決定）。原因：部分方案上 Fable 當 advisor 要先一次性同意把 Fable 用量記到 usage credits，那是真的錢，而 Stan 的 extra usage 是關的。

Claude Code advisor 的事實（https://code.claude.com/docs/en/advisor ，2026-11-14 讀）：
- 用 `/advisor`、`advisorModel` 設定鍵或 `--advisor` 啟動旗標設；alias `fable`、`opus`、`sonnet` 指向 CC 內建的各家預設版本；`CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` 整個關掉。中途開關 advisor 不會讓主模型的 cache 失效。
- 搭配表：Fable 5.2 主模型只收 Fable 5.2 advisor；Fable 5.1 主模型收 Fable 5.2 或 5.1；Opus 5 與 Opus 5.5 主模型收 Fable 或 Opus 5 以上；主模型是 Fable 時 CC 不套用 Opus 或 Sonnet advisor。
- 版本：Fable 5.2 當 advisor 要 v2.1.321 起，Fable 5.1 要 v2.1.257 起，Haiku 5.5 當主模型或 advisor 要 v2.1.293 起。
- 計費：advisor 在決策點才被叫，不是每回合；API 計費照 advisor 模型單價；訂閱方案算進方案額度，但 Fable advisor 在 Fable 走 usage credits 的方案上記到 usage credits。部分方案要一次性同意，同意前 `/advisor fable` 不會存，會被導向 `/model fable`。
- 只能在 Anthropic API 或 Claude Platform on AWS 用，Bedrock、Google Cloud Agent Platform、Microsoft Foundry 沒有。

API 端（advisor tool beta，`advisor_20260301`、beta header `advisor-tool-2026-03-01`）：Fable 5.2 或 Mythos 5.2 executor 只收 Fable 5.2 或 Mythos 5.2 當 advisor，其他回 400；新一代 advisor 回傳加密的 `advisor_redacted_result`，client 讀不到建議內容；移除 advisor 或改它的 model、max_uses、max_tokens、caching 算改 tools，會讓歷史 thinking block 失效。

## Opus 5.5 專屬 prompt 技巧（官方指南摘錄）

- **multi-agent 給時間訊號**：每則回傳訊息尾巴加 `elapsed 340s / 1200s`，模型會為了趕上而多開平行；沒預算就只給 elapsed + 一句「time matters」。實測小隊完成更快、品質持平。（Fable 5.2 不適用：小隊只換到速度，token 更多，單 agent 跑，見 `fable52-system-card.md`。）
- **多 app 自動化先探索再動手**：一句「Before taking any action, explore broadly with tool calls…」讓正確率明顯上升；代價是多幾個 tool call。
- **貼上內容加標籤**：`<pasted_content id="隨機碼">` 包住使用者貼來的文字 + system prompt 說明，對間接注入更硬。
- **前端不要只說「別像 AI」**：要點名具體模式（奶油底色、斜體標題強調字、01/02/03 章節號、等寬標籤、藥丸按鈕），它才會換掉。
- **chat 多輪回頭想**：Opus 5.5 會在後續短問時重審前一答；要它當已定案就在 system prompt 末尾加兩句（官方範本），但這也會讓它較少主動指出前答錯誤。
- **視覺輸入**：先拔掉為舊模型做的 vision 鷹架再測；最密的圖給高解析度 + crop 工具仍有幫助，高 effort 對工程圖有用、對圖表沒用。
