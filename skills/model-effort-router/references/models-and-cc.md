# 模型規格、Claude Code 現況與 prompt 技巧

寫 API 整合、設定 Claude Code、查 alias 與預設值時讀這份。

## 模型特性速查

| | Sonnet 5.5（$2/$10） | Opus 5.5（$4/$20） | Fable 5.1（$10/$50） |
|---|---|---|---|
| 定位 | 範圍明確的日常 coding、修 bug、文件；high 最划算 | 預設起點；agentic coding / 知識工作 / 電腦操作最強 | 官方「最高可用能力」，只在 Opus 5.5 高檔仍不夠時 |
| cutoff | 2026-06 | 2026-06 | 2026-06 |
| context / max output | 1M / 128k（Batch beta 300k） | 1M / 128k | 1M / 128k |
| cache read | $0.10（base 5%，2026-10-07 起減半） | $0.20（base 5%） | $0.25（base 2.5%） |
| thinking | 永遠開；API 送 `disabled` 回 400，最低設定改 `between_tools`（只配 low~high）；CC 關不掉 | 永遠開、關不掉（`disabled`/`budget_tokens` 都 400） | 永遠開、關不掉；raw CoT 永不回傳 |
| 分類器 | 第一個帶 cyber 分類器的 Sonnet：cyber、frontier_llm 擋下改送 Sonnet 5；bio、reasoning_extraction、general_harms 無 fallback | cyber（與 Fable 同級，擋下改送 Opus 4.8）、bio（同 Fable 5.1，擋下改送 Opus 5）、frontier_llm（改送 Opus 5）、reasoning_extraction（無 fallback） | 同左 |
| prompt 脾氣 | 沿用 Sonnet 5 prompt 即可；low 可能沒跑測試就回報完成；low/medium 長任務會中途停下來問；各檔都愛順手加測試與文件；xhigh/max 會自己開 review 輪與 subagent；偶爾 tool 名大小寫打錯 | 出手快、回報清楚；長程任務會用純文字回報而早停；前端沒指示會套「AI 通用款」 | 過度指令化反而降質；平行 tool call 變少要提醒；小改愛整檔重寫 |
| fast mode | 無 | `/fast`，$8/$40 | 無 |

Haiku 5.5（$0.10/$0.50，prompt 超過 100K 變 $0.50/$2.50；1M context；預設 medium）的完整規格在 `model-picks.md`「Haiku 5.5 什麼時候選」。

Sonnet 5 列為 legacy 但仍 Active（退役不早於 2027-06-30）、$2/$10 定價永久維持、cutoff 2026-01、預設 high、thinking 可關、無分類器；它是 Sonnet 5.5 cyber refusal 的 fallback 目標。

Opus 5 降為 legacy（$5/$25、預設 high、thinking 可關到 high、fast mode $10/$50），仍可用；分類器較 Opus 5.5 寬鬆，是 bio/frontier_llm 類 refusal 的官方 fallback 目標。

## Claude Code 現況（v2.1.284 起的內容，2026-10-13 補到 v2.1.296）

- 預設模型：Pro/Max/Team/Enterprise/API 全部 Opus 5.5（Pro 與 Team Standard 也從 Sonnet 改成 Opus）；Sonnet 5.5 不是任何方案的預設。`opus` alias → Opus 5.5；`fable`/`best` → Fable 5.1；`sonnet` → Sonnet 5.5（v2.1.284 起，只限 Anthropic API；Bedrock/Agent Platform/Foundry 仍指向 Sonnet 4.5）；`opusplan` → Opus 5.5 規劃 + `sonnet` 執行（Anthropic API 上即 Sonnet 5.5，由兩句文件推得）。規劃與執行之間切換算換模型，cache 會重讀。
- Sonnet 5.5 需要 CC v2.1.284 起；固定 1M context，沒有 200K 版、不用 usage credits，約 967K 自動 compact。
- effort 解析順序（主 session）：`CLAUDE_CODE_EFFORT_LEVEL` ＞ `--effort` / `/effort` ＞ `modelSettings` 逐模型 ＞ 頂層 `effortLevel`（**Opus 5.5 及之後的模型不吃 user settings 那個**）＞ 模型預設（Opus 5.5 / Sonnet 5.5 / Haiku 5.5 = medium，Fable 5.1 = high）。
- effort 解析順序（subagent）：`CLAUDE_CODE_EFFORT_LEVEL` ＞ Agent 工具派工時帶的 `effort`（v2.1.292 起，resume 也保留）＞ 定義檔 frontmatter 的 `effort:` ＞ 沒寫時大概跟 session 走（文件只暗示）。skill frontmatter 的 `effort:` 在該 skill 執行時生效，同樣蓋不過環境變數。`maxEffortLevel` 對以上全部設上限。
- `/effort` 的存與不存：不帶參數開滑桿（v2.1.257 起），按 `s` 只套這個 session、按 Enter 存；直接打 `/effort high` 也會存。存的位置是 user settings 的 `modelSettings`，每個模型各一份；`/effort auto` 清掉這個模型的存檔。`/model` 選模型時按左右鍵調 effort，Enter 存、`s` 不存。`--effort` 只管這次啟動。`max` 只能當次 session，`modelSettings` 只收 low 到 xhigh。
- `ultrathink` 寫在 prompt 裡：這一回合加一段想深一點的指示，送給 API 的 effort 不變。`/tasks` 列出每個 subagent 實際的模型與 effort。
- Stan 現況（2026-10-13 查 `~/.claude/settings.json`）：頂層 `effortLevel: "high"`、沒有 `modelSettings`、沒設 `CLAUDE_CODE_EFFORT_LEVEL`。所以主 session 的 Opus 5.5 原本跑 medium，頂層鍵只剩 Fable 5.1 吃得到；agent 定義檔的 effort 都有效。品質優先版要 Stan 在 session 打 `/effort high` 存進 `modelSettings`。2026-10-14 更新：桌面版打 `/effort high` 沒存檔，已手動寫入 `modelSettings["claude-opus-5-5"].effortLevel: "high"`（commit `5d2c28a`）；另有 `switchModelsOnFlag: false`（CLI 設定說明：訊息被 safeguard 標記時 session 暫停，不自動換模型），所以 Stan 的 CC 不會自動 fallback 到 Opus 4.8。
- 不支援的檔位自動退到該模型最高可用檔（xhigh 在 Opus 4.6 跑成 high）。
- `/fast` 預設模型 Opus 5.5；目前模型不支援 fast 時會自動切到 Opus。
- Haiku 5.5（model ID `claude-haiku-5-5`，2026-10-07 發佈）v2.1.293 起是 Anthropic API 上的預設 Haiku，`haiku` 別名指向它；1M context、$0.10/$0.50（prompt 超過 100K 變 $0.50/$2.50）、五檔 effort、預設 medium。Haiku 4.5（$1/$5、200K、不支援 effort）退役日不早於 2026-10-15，不再使用。Stan 2026-10-13 解禁 Haiku 5.5（硬規則 14）。
- `/checkup prompt-audit [路徑]`（v2.1.283 起，`/doctor` 的別名）：掃 CLAUDE.md、rules、skills、commands、subagents、output styles，找過時路徑、互相矛盾、「CRITICAL/MUST」施壓語氣、「think harder」這類對永遠開 thinking 的模型無效的句子、寫死的模型名。只提案不改檔；不讀 settings/hooks/MCP 設定。兩份官方文件對預設是否掃 `~/.claude/` 說法不一，路徑要自己給。

## Opus 5.5 專屬 prompt 技巧（官方指南摘錄）

- **multi-agent 給時間訊號**：每則回傳訊息尾巴加 `elapsed 340s / 1200s`，模型會為了趕上而多開平行；沒預算就只給 elapsed + 一句「time matters」。實測小隊完成更快、品質持平。
- **多 app 自動化先探索再動手**：一句「Before taking any action, explore broadly with tool calls…」讓正確率明顯上升；代價是多幾個 tool call。
- **貼上內容加標籤**：`<pasted_content id="隨機碼">` 包住使用者貼來的文字 + system prompt 說明，對間接注入更硬。
- **前端不要只說「別像 AI」**：要點名具體模式（奶油底色、斜體標題強調字、01/02/03 章節號、等寬標籤、藥丸按鈕），它才會換掉。
- **chat 多輪回頭想**：Opus 5.5 會在後續短問時重審前一答；要它當已定案就在 system prompt 末尾加兩句（官方範本），但這也會讓它較少主動指出前答錯誤。
- **視覺輸入**：先拔掉為舊模型做的 vision 鷹架再測；最密的圖給高解析度 + crop 工具仍有幫助，高 effort 對工程圖有用、對圖表沒用。
