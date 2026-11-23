---
name: skill-routing
description: 重疊 skill 的分流表（除錯、規劃、逼問、發想、code review、簡化、前端、安全、完工驗證、git、寫 skill）。一個任務同時命中兩個以上 skill、不確定用哪個時查；裝了新 skill/plugin 要判重疊時也查。表上沒列的領域＝沒重疊，直接選。
user-invocable: true
---

# Skill Routing

同領域有多個 skill 時照表選預設，只有「改用時機」描述的情況才換。標 ❄️ 的選項已冷藏，情境出現時先報告再復原，不要沉默跳過也不要假裝它還在。復原方式：個人 skill 在 `~/.claude/cold/skills/`，`mv` 回 `~/.claude/skills/`（或刪 `settings.json` 的 `skillOverrides` 對應行）；plugin 把 `enabledPlugins` 該行改回 `true`；重開 session 生效。

## 分流表

| 領域 | 預設 | 改用時機 |
|---|---|---|
| 寫測試 / TDD | 沒有專用 skill，照通則 | 通則：先看測試紅再實作；一次一個 vertical slice；預期值來自獨立真值，別用同一套算法反推 |
| 除錯 | 一般 bug 直接修，先重現再改 | flaky、效能回歸、多元件、或第一次就猜錯 → `diagnosing-bugs`（先建紅燈可重現迴圈再查）；連 3 次修不好 → 停下回報 Stan，列出可能錯的假設 |
| 規劃 / spec | `guided-dev`（產品決策給人、技術決策給 Claude、切可驗證 slice） | 需求還講不清 → `grilling` 的「還沒有計畫」段；步驟寫進 `tasks/todo.md`（CLAUDE.md 第 5 條） |
| 逼問既有計畫 | `grilling`（一次一題，能查 codebase 就自己查） | 還沒計畫、先抓 who/why/success → `grilling` 的「還沒有計畫」段（interview-me 的規則已併入） |
| 發想 | `grilling` 的「還沒有計畫」段（一次一題收斂需求） | 已知要做什麼、但有多組可行解要拉開（命名、API 表面、架構取捨）→ `adhd`（5 個框架平行發散，約 10 個 agent、成本 5-10x；題目有唯一標準答案時它會自行 abort） |
| code review | 內建 `/code-review` | 收到 maintainer 回饋 → `oss-factory` 的「收到 maintainer review」段（receiving-code-review 的規則已併入） |
| 程式簡化 | 內建 `/simplify` | 無。通則：既有測試要不改就過，要改測試才過＝行為變了 |
| 效能 | 沒有專用 skill：先量、再改、再量 | 線上單頁深度稽核且有 Chrome DevTools MCP → ❄️ `cloudflare:web-perf`（plugin 已停用）；改壞才變慢 → `diagnosing-bugs` |
| 前端視覺 / 設計品質 | `impeccable`（硬規則、absolute bans、slop test；`critique`/`audit` 可當設計審查） | 元件庫慣例 → ❄️ `shadcn`；❄️ `frontend-design` 只在 impeccable 沒蓋到的具體情境復原用，冷藏不是判死刑 |
| API / seam / 模組形狀 | 沒有專用 skill | deep-module / deletion test 方法論 → ❄️ `codebase-design` |
| 安全 | `security-guidance`（edit/commit 時背景自動跑，不用主動叫） | 對整個 codebase 深度獵洞、找可實際利用的漏洞 → `security-audit`（很吃 token，小改動別用）；安全敏感的實作（auth、秘鑰、驗證碼、LLM 輸出進系統）→ 派 `security-executor` agent；掃描器比對 → ❄️ `static-analysis` |
| 完工驗證 | 跑指令拿證據；非瑣碎改動派 `verifier` agent | 無 |
| git | 照 CLAUDE.md 第 5 條（一功能一版號一 commit） | 卡在 merge/rebase 衝突 → `resolving-merge-conflicts`（找每個衝突的原始意圖、逐 hunk 解、跑專案自己的檢查、絕不 `--abort`） |
| context 工程 | 沒有專用 skill | ❄️ `context-compression` / `context-optimization` |
| 寫 / 改 skill | `writing-great-skills`（文筆與結構） | eval / benchmark → ❄️ `skill-creator`（plugin 已停用）。通則：改 skill 前先在沒有它的情況下跑一次同樣的情境，逐字記下模型怎麼繞過或找藉口，改完再跑一次對照；沒做這個對照就不算驗證過 |

`superpowers` 與 `agent-skills` 兩個 plugin 2026-11-23 移除，留下的規則已寫進 CLAUDE.md、agent 定義與上面幾列。要裝回：`claude plugin install superpowers@superpowers-marketplace` 或 `agent-skills@addy-agent-skills`；superpowers 裝回後要重套 `~/.claude/overlays/superpowers-stan-overlay.md`，否則 SessionStart 注入會回來。

## 各管各的（不重疊，直接用）

- 影片轉稿 / 摘要 → `transcribe`、`video-lens`
- 去 AI 寫作痕跡 → `humanizer`（英）/ `humanizer-zh-tw`（繁中，含學術 Academic Mode）
- PDF → Markdown：要圖檔切出、複雜表格、掃描檔、公式轉 LaTeX、離線 → `mineru`（本機 CPU 慢；雷：底線跳脫、中英黏字、偶吞符號，要 regex 清）。要乾淨中文正文、要快 → ❄️ `mistral-ocr-tts`（雷：頁碼混入、圖只給死連結）
- docx / pptx / pdf / xlsx 生成或編輯 → 桌面 app 內建 anthropic-skills（`document-skills` plugin 已停用）
- 把專案部落知識固化成 skill 庫 → `project-skill-library`（Phase 0 閘門：部落知識、夭折路線史、還會繼續做，三缺一就只寫 HANDOFF.md）
- Claude ↔ Codex 交接 → `cross-model-handoff`（給 Codex 的 brief 剝掉「先給計畫、回報進度」；AGENTS.md 只放硬約束與驗證指令）
- 用 TypeSafe API（typed 判斷／機率，不生成文字）做路由、排序、抽取、驗證 → `typesafe:typesafe-ai`（2026-09-19 裝；要 `TYPESAFE_API_KEY`）
- 理解大型不熟的 codebase → `graphify` CLI（ad-hoc `graphify extract <程式碼子集>` 建圖再 `explain`/`affected`；別跑 `graphify install`，會寫常駐 hook）
- 冷藏中、情境出現先復原：Android → ❄️ `chrisbanes-skills`；Chrome 擴充 → ❄️ `modern-web-guidance`；DDD → ❄️ `domain-modeling`；pre-commit → ❄️ `setup-pre-commit`；拋棄式原型 → ❄️ `prototype`；成長 / AARRR → ❄️ `product-growth`；12-factor agent 系統 → ❄️ `12-factor-*`；投研報告 → ❄️ `report-verifier` / `upstream-insights-report` / `adversarial-review`

## 沒有 skill 涵蓋的

發版號（semver、tag、CHANGELOG）照全域 CLAUDE.md 第 5 條手動做：每功能一版號、commit、CHANGELOG。

## 維護

表有變更就同步兩處：`~/.claude/hooks/skill-rules.json`（`why` 欄＝濃縮判準，`skills` 陣列第一個＝預設）和全域 CLAUDE.md 第 1 條的摘要。新工具該不該納入走 `new-skill`，結論寫回本表並在同目錄 `EVALUATIONS.md` 追加一列。上游同步層級（vendor、overlay patch、自寫、fork）與對帳閉環見 `MAINTENANCE.md`；歷史紀錄見 `CHANGELOG.md`。
