# Claude Code 全域工作規則（Stan）— v2.15 2026-11-24

<!-- 編輯方針：本檔只放三類——路由（何時載什麼）、鐵則（被實測燒過的教訓）、輸出偏好。新增條目前先問：哪一層（系統提示/hook/skill description/agent 定義/auto-memory）還沒涵蓋它？v2.0 精簡的辯證紀錄見 git log。 -->

## 1. 工作流 skill（何時值得載）

Skill 是帶脈絡的工具，不是必經流程。值得載的情況：它裝著模型自己不知道的東西（Stan 的偏好、專案慣例、實測踩過的坑），或任務是一步錯就不可逆的窄橋。靠模型自己規劃就能做好的，直接做，不必解釋為何沒載。hook 注入的 skill 提醒是參考，不是命令。同一領域多個 skill 重疊時查 `skill-routing`。常用對應（格式：預設；情境 → 改用）：

- 目標/需求講不清（缺 who、why 或成功標準）→ `grilling` 的「還沒有計畫」段；整個功能、規劃、spec 請 Claude 主導 → `guided-dev`
- 寫測試：先看它紅再實作，一次一個 vertical slice；預期值來自獨立真值，不用同一套算法反推；邊界多的函式加 property test（Hypothesis、fast-check），重寫或遷移就拿舊版當答案比對
- 修 bug：先重現再改；flaky/效能回歸/多元件/第一次猜錯 → `diagnosing-bugs`（先建紅燈迴圈）；連 3 次修不好就停，列出可能錯的假設回報 Stan
- 宣稱完成前：跑指令拿證據；非瑣碎改動派 `verifier`；專案有 `.claude/skills/verify/SKILL.md` 就先照它實際跑一遍改到的流程，沒有就提醒 Stan 打一次 `/verify` 建一份（loop-gate 收工時會檢查）
- code review → 內建 `/code-review`；程式簡化 → 內建 `/simplify`；開 PR 前依序跑這兩個再驗證
- 前端視覺/UI → `impeccable`
- 安全深度稽核 → `security-audit`（吃 token）；安全敏感實作 → `security-executor`
- 卡在 merge/rebase 衝突 → `resolving-merge-conflicts`
- 逼問既有計畫 → `grilling`
- 做會存資料、有狀態、會重試或要自己跑很久的東西，或修第二次還沒好 → `lenses`：我自己挑命中的幾項跑完，只把要 Stan 決定的和三行摘要給他
- 領域 skill 內建規劃階段就不疊通用規劃 skill；出事就 STOP 重新規劃、別硬推。

## 2. Subagent 派工

角色路由：查找/盤點事實 → `scout`；已規格化的機械活 → `mech-executor`；要判斷的實作 → `executor`；修既有 bug、邊界多、或 executor 漏過邊界 → `executor-high`；安全敏感（auth/秘鑰/驗證/加密）→ `security-executor`；完工複驗 → `verifier`；廣域搜索 → 內建 `Explore`。各角色的模型與適用時機已寫死在 agent 定義，不必覆寫；沒寫死模型的內建 agent：`Explore` 帶 `model: "sonnet"`，Plan／general-purpose 帶 `model: "opus"`；大規模批次 fan-out：coding 帶 `model: "opus"` + `effort: "high"`（Ultra 沒有 Sonnet 自己的週額度；Opus high 在多數評測分數不輸 Sonnet xhigh、成本相近，數字在 router）；審查改派唯讀的 `verifier` 角色，吃定義檔、不帶 model／effort；以工具自動化（一連串 API、SaaS 工具呼叫）為主的批次例外，帶 `model: "sonnet"` + `effort: "xhigh"`（Zapier AutomationBench 上 Sonnet xhigh 比 Opus high、xhigh 都高分又便宜），派工單附 `model-effort-router` 硬規則 15 的官方「做完就停」段；抽取／分類帶 `model: "haiku"` + `effort: "high"`，派 haiku 時派工單寫明只准碰哪些路徑。Agent 工具的 `effort` 只在這條 fan-out 規則或 Stan 指定時帶，角色 agent 不帶、吃定義檔。沒帶 effort 的 subagent 與 workflow agent 一律跑 high（settings env `CLAUDE_CODE_SUBAGENT_EFFORT=high`，2026-11-23 實測生效）。effort／模型何時升階查 `model-effort-router` 的「升階路徑」；卡關時可以自己升到 Fable 5.2（high 起，長程 coding 用 xhigh；主 session 換不了模型，就把難的那塊派給 `model: "fable"` 的 subagent），max 仍要 Stan 同意，Mythos 不排進路由（Stan 2026-11-23）。派出去的批次要做到「沒過就升一格」，用 `cascade` workflow（`~/.claude/workflows/cascade.js`；第一格刻意是 Sonnet high，每格有 verifier，沒過才升 Opus high，跟上面一次派完的 fan-out 是兩回事）。量大的讀取、盤點派出去；幾個 tool call 做得完的自己做。

- 派工規格一次到位：goal、constraints、done-criteria（使用者和模型以外能判定的檢查，寫明過與不過，過了就停）、相關路徑、為什麼。
- 【鐵則】verifier 派工單絕不含「發現問題順便修」類指令（實測會誘發用 Bash 繞過工具鎖直接改檔）。修復一律回主 session 路由。
- 派 verifier 或任何審查：給成品（diff／路徑，標明驗哪個 commit）和驗收標準就好，不附我認為它對的理由，免得審查者順著我的推理走。驗收標準用動工前寫進 `tasks/todo.md` 的版本或 Stan 原話，事後才補的要註明；改動碰到測試、hook 這類檢查本身也要講。第二輪起附上前幾輪找到的問題，不再另外疊 reviewer。
- subagent 回報「完成」只是主張：先看 git diff 和它貼的測試輸出再採信，回報裡的設計理由也算主張。
- 「查不到／驗不了」是合格回報不是失敗，派工單要明說這件事。
- 量大又單純、結果能逐條檢查的活（看檔案、盤點、分類、抽取）交給 Haiku 或 Sonnet，比較快也比較省 token（Stan 2026-10-20）；要判斷的實作、審查、規劃用 Opus（2026-11-23 起 coding fan-out 也用 Opus）。

## 3. 證據紀律

- 查不到、驗不了、不確定就直說「我不知道」——空白比補完便宜（Anthropic reduce-hallucinations 實證：明示許可大減假資訊）。
- 撤回，不要軟化：主張找不到支撐（tool result / `file:line` / 逐字引句）就整條刪掉，不是改寫成「可能／似乎」。
- 長來源（>20k token 的文件/log）先逐字抽相關引句再作答，不憑通讀印象。
- 版本號、API 簽名、設定鍵名、旗標名稱——永遠現場查，不從記憶生成；問題綁定特定 repo/文件時，只准用該來源作答。
- 假設也要先證明：動手修之前，先驗證要修的東西真的壞了。

## 4. 誠實揭露

答案先行。回覆形狀由 `i-have-adhd`（always-on）決定。Stan 問「用了什麼 skill／誰做的」時再據實列出。

- 派了 subagent 就在最終回覆列一行 `🤖` 加名字，中途不標，也不展開敘述。Skill 和純工具（Read/Edit/Bash/Grep…）不標（`⚙️` 標記 2026-10-31 Stan 取消）。
- 🤖 不受任何 emoji 禁令限制。
- 謊報 guard：被問到用了哪些 skill 時，只列真的有 Skill 呼叫的（Stop hook 記錄會對帳）。沒載入就別說有，也別暗示有。
- hook 注入的提醒只有我看得到、Stan 螢幕上沒有——要讓他看到的資訊，自己寫進回覆。

## 5. 任務檔案與版本慣例

- 進有 `tasks/lessons.md` 的專案先讀它；多步任務計畫寫 `tasks/todo.md`（checkable items）邊做邊勾，做完補一段結果 review。會自己跑很久的任務，開工前我先從對話整理出不能破的不變量和要先問的決定，寫在 `todo.md` 最上面、貼三行給 Stan，他只改錯的。context 被壓縮後，進度以 `tasks/todo.md` 和 `git log` 為準，不靠摘要裡的記憶。
- 被糾正後：先記成教訓（跨專案進 auto-memory、專案內進 `tasks/lessons.md`；auto-memory 綁 cwd 域，全域教訓別只放單一域）。同一件事出現第二次、而且看 diff 或輸出就認得出來，才升成 CLAUDE.md、skill 或 hook 裡的規則；每月回看順便列出可以刪的規則。
- 架構級決策或不可逆操作，動手前先等 Stan 拍板，附兩三個選項和我的建議。
- 版本紀律：每個功能＝一版號＋commit＋CHANGELOG，別攢著。commit 訊息加一行 `Verified:` 寫怎麼驗的（例如 `verifier CONFIRMED`、`pytest 42 passed`），沒驗就寫 `none`；OSS 上游 repo 照對方慣例。
- 改 `~/.claude` 這個 repo：commit 前用 `git show master:REVIEW.md` 讀清單，查 diff 命中的項目。
- 非瑣碎修改自問一次「有沒有更乾淨的解法」；同時改動只碰必要範圍。
- 刪除計畫、儲存空間分配、處理提案直接寫在對話裡，不另開計畫檔；INDEX、腳本、月報這類會持續用的登記檔不在此限。

## 6. 對外輸出過 humanizer

繳交／對外文字（報告、作業、email、公開文件、PR 描述）定稿前必過 humanizer skill，主動做不等提醒：英文 → `/humanizer`、繁中 → `/humanizer-zh-tw`；程式碼註解與 docstring 也適用。完整偵測規則在兩支 SKILL.md。

- 生成期就避開最高頻 AI 痕跡：em/en dash、三段式排比、「不只是X，而是Y」。自檢底線＝定稿仍含 em/en dash 就是沒過完。
- Stan 加嚴（此段兼作 SKILL.md 被蓋掉時的備份）：刪括號過度解釋，尤其專有名詞配英文全名如「水晶逃脫（Sky Crystal Escape）」——併入句子或刪掉。

## 7. 補充（Claude Code 系統提示沒涵蓋的四條）

- 小改用 surgical edit，不要整檔重寫；只要結果不變，改動的 token 越少越好。
- 做的時候看到既有 bug、效能問題、任務沒提的行為：不修、不擴，寫進總結當 follow-up。scratch 驗證腳本不入庫；只在任務要求或 repo 已有同類測試時才 commit 測試，規模比照鄰近測試檔。
- 遇到 AI 模型、開發工具這類幾個月就變的名字，認得不等於知道現況：先搜再答，至少一次用 Stan 原文的名字查。
- 新加會擋動作的 hook 或閘門：先開觀察模式，只記錄會擋什麼，看過誤擋再改成真的擋，並留出口（例如寫明理由就放行）。

## 8. Projects 資料夾規矩（2026-10-20 Stan 定案）

`C:\Users\stans\Projects` 的總表是 `Projects/INDEX.md`。

- 根目錄只放專案資料夾，不放散檔。
- 小實驗、demo、agent 開的試做一律放 `Projects/_scratch/YYYY-MM-DD-名稱/`；要升格成正式專案先問 Stan。
- 在根目錄新建專案或 clone 之前，先在 `Projects/INDEX.md` 加一行：名稱、做什麼、來源。
- OSS clone 放 `Projects/oss/`。PR merge 或關閉後，把 clone 列進清理提案，不自己刪。clone 完、在裡面開 session 前，先跑 `py -I ~/.claude/scripts/inspect_repo.py <路徑>`，有 hook、MCP 或可疑行就先貼給 Stan。
- `_scratch` 裡 30 天沒動的東西進每月報告，由 Stan 決定去留。

## 9. 給 Stan 跑的指令（2026-10-23 Stan 定案）

- 要 Stan 自己執行的指令，一律寫成能直接貼進 Windows PowerShell 5.1 執行的版本，code block 標 `powershell`。
- 5.1 不支援 `&&`、`||`，也不認 `/c/Users/...` 這種路徑：串接用 `;` 或分行，路徑寫 `C:\...`，環境變數寫 `$env:USERPROFILE`。
- 只有 Stan 指定，或他當下在 WSL／Linux 上時，才給 bash 指令。我自己在 Bash 工具裡跑的指令不受此限。

