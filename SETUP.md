# Stan Claude Harness — Setup 地圖

> 這份索引是「我的 Claude setup 有哪些東西、放在哪」的權威答案。
> 動過任何一塊就順手更新這裡。最後更新：2026-11-24（loop-gate 1.1.0、lenses、inspect_repo、autosync 加 gitleaks、月度回看、REVIEW.md）。

## 大原則：一個 repo

整個自建 harness ＝ 本資料夾 `~\.claude\` ＝ GitHub repo
**`stantheman0128/stan-claude-harness`**（public；原名 stan-claude-config，2026-07-12 改名）。
**push 一次＝全部備份完成**。唯二例外見「不進版控的東西」。

## 內容物

| 東西 | 路徑 | 說明 |
|---|---|---|
| 全域指令 | `CLAUDE.md` | 工作流規則 v2.15：何時載 skill、subagent 派工、證據紀律、版本與 commit 慣例、humanizer、Projects 資料夾規矩 |
| commit 前清單 | `REVIEW.md` | 改這個 repo 時照 diff 命中的項目查（hook、plugin、CLAUDE.md、settings 等 14 列）；一律讀 master 版：`git show master:REVIEW.md` |
| 設定 | `settings.json` | 權限、hooks 掛載、enabledPlugins、marketplace 指標（指向下面的 local-plugins） |
| 狀態列 | `statusline.sh` | 自製 statusline（context%、effort 顯示） |
| Hooks | `hooks\` | 17 支：skill 觸發系統 3 支＋規則檔、事件觸發 skill 提醒 1 支（event-skill-nudge.py：對外文字前提醒 humanizer、git 衝突時提醒 resolving-merge-conflicts）、守門 3 支（careful、mode、research）、session 中文名、ADHD 常駐、claude-mem 6 支、overlay 檢查 1 支（`overlays\`）、harness 自動同步 1 支（harness-autosync.py） |
| Agents | `agents\` | pilotfish 分工制：scout / mech-executor / executor / executor-high / security-executor / verifier / quant-analyst / deep-research-agent |
| Workflows | `workflows\` | 存檔的 dynamic workflow，用 `Workflow({name})` 叫：`cascade.js`（2026-11-23，批次工作便宜的先做、verifier 驗不過就升一格，Sonnet high → Opus high → Fable high → Fable xhigh，到頂就停） |
| Skills | `skills\` | 34 資料夾，**全量進版控**，用途見 `skills\CATALOG.md`；2026-11-24 新增 `lenses`（動手前回看清單：隱含狀態機、不變量、故障演練等 14 項）；humanizer×2 例外見下 |
| Overlays | `overlays\` | plugin overlay patch 檔（impeccable 5 條 harvest 等）——plugin 升版被蓋掉時的還原依據 |
| 舊 slash commands | `commands\` | 17 支 legacy（reels、api:*、misc:*、supabase:*、ui:* 等），多數已冷藏、檔案留存 |
| skill 狀態資料 | `skill-data\` | skill 的執行歷史檔（adversarial-review、upstream-insights-report） |
| **自製 plugin 市集** | `local-plugins\` | marketplace 名 `stan-local-plugins`：**burn-credits** 2.0.0（`/burn` 掃全專案找問題批量修，燒剩餘額度；原名 project-sweep）、**loop-gate** 1.1.1（Stop hook 機器驗證 gate，加上 e2e gate 觀察模式）、**quota-pacer** 0.8.5（額度感知節奏器，接近上限前收手寫交接） |
| 工具腳本 | `scripts\` | `inspect_repo.py`：陌生 repo 開 session 前列出 hook、MCP、可疑指令行，只讀不執行，會跟 CLAUDE.md 的 `@import`、掃子資料夾的指令檔，碰到 symlink 或讀不完就判成掃描不完整（`py -I ~\.claude\scripts\inspect_repo.py <路徑>`）；`codex-style-audit.py`：統計 codex 輸出風格的中途與最終訊息；`Fix-ClaudeDesktopHives.ps1`：Claude Desktop 異常關閉後殘留 registry hive、開不起來時用 |
| 固定情境測試 | `evals\harness-rules\` | 用 `claude -p` 在暫時 repo 測鐵則與 agent 定義：verifier 不准修、秘鑰檔只用 Glob、scout 帶 file:line、lenses 有無對照、中文沒有破折號。`python -B evals\harness-rules\run.py`，一次約 8 分鐘，輸出放 `%TEMP%\harness-eval\`，不進 repo |
| **運維** | `ops\check-skills-update\` | skill 上游更新檢查（原 claude-setup / drift sweep）：排程 `CheckSkillsUpdate` 每週一 09:23，雙篩自動收錄、四硬閘門、備份回滾 |
| 文件 | `docs\specs\`、`docs\plans\` | 設計 spec 與實作計畫（loop-gate、本次重構等） |

## 不進版控的東西（刻意）

| 東西 | 路徑 | 原因與備份方式 |
|---|---|---|
| 記憶 | `projects\C--Users-stans-Projects\memory\` | 含各專案細節，只留本機 |
| humanizer 客製版 | `skills\humanizer\`、`skills\humanizer-zh-tw\` | 各自是獨立 git repo（origin=上游，刻意 fetch 不 pull）；**備份 = private repos `humanizer-stan`、`humanizer-zh-tw-stan`（backup remote，客製後 `git push backup main`）** |
| 執行期狀態 | `/loop-gate\`、`hook-health.log`、`/jobs\`、`/security\`、`/skill-usage\` 等 | runtime，見 .gitignore |
| 審查與月報 | `audits\` | prompt audit、官方文章 takeaways、月度回看報告 `harness-monthly\<YYYY-MM>.md`，只留本機 |
| gitleaks 紀錄 | `hooks\harness-autosync.log` | 會寫出哪個檔第幾行疑似秘鑰，不能進公開 repo |
| 休眠 app 安裝版 | `auto-hibernate\` | 可攜版有自己的 repo：`Projects\bedtime-hibernate`（GitHub public） |
| ops 的 reports/backups | `ops\check-skills-update\{reports,backups}\` | 產出物與回滾備份，只留本機 |

## loop-gate 速查（掛驗證 gate 的專案）

- 掛了 gate 的專案 = 有 `.claude\verify.json` 且經信任註冊者。目前：`chrome-extensions`、`payclaw`、`meeting-translator`（887 個測試加型別檢查，約 20 秒）、`rc-anchor`、`remote-display-profiles`、`krillion`（後三個沒有測試，只查語法或編譯）、`~\.claude` 自身（dogfood：selftest 當 verify 命令）。
- 幫新專案掛：對 Claude 說「幫 X 專案掛驗證 gate」或「用 loop engineering 做」，或手動：
  寫 verify.json → `py ~\.claude\local-plugins\loop-gate\scripts\trust_manifest.py <專案根>`。
- 信任過的 verify.json 被改了：gate 跳過不跑，當下顯示一行提醒，重新跑 trust_manifest.py 才恢復（1.1.0 起）。
- e2e gate（1.1.0 起）：一個 session 改了 40 行以上或 3 個以上程式檔（文件、測試、lockfile 不算），收工時找實際驗證過的證據：跑了 verify skill、派了 verifier、讀了專案的 `.claude\skills\verify\SKILL.md`、Stan 打了 `/verify`，或最後回覆有 `Verified:` 行。另外 `git commit` 沒有 `Verified:` 行、`gh pr create` 前沒跑 code-review 也會記錄。commit 進 `Projects\oss` 底下的 repo 不查；1.1.1 起看 `git -C`、`cd` 實際指到的 repo，也讀 `-F` 檔和 `--amend` 重用的訊息，判斷不出來就不記。
  - 設定檔 `~\.claude\loop-gate\e2e_gate.json`，`"mode"` 可設 `observe`（預設，只記到同資料夾的 `e2e-gate.jsonl`）、`enforce`（同一 session 最多擋 2 次）、`off`。
  - 專案沒有 `.claude\skills\verify\SKILL.md` 時，會提醒 Stan 打一次 `/verify` 建一份。
  - commit 檢查還認不得 `git --no-pager commit`、`git -P commit`、alias 和 `bash -c "git commit ..."`，這些會漏記；改成 enforce 前先補。enforce 擋 commit 不限次數，訊息寫一行 `Verified:`（沒驗就寫 `none`）就放行。
- 改 plugin 的 hook 前後跑 selftest：`py ~\.claude\local-plugins\loop-gate\scripts\selftest\run.py`（36 案例須全綠）。

## 自動化迴圈（會自己跑的東西）

| 迴圈 | 觸發 | 狀態 |
|---|---|---|
| loop-gate 驗證 gate | 每次 Stop（掛 manifest 的專案） | chrome-extensions、payclaw、meeting-translator、rc-anchor、remote-display-profiles、krillion、harness 自身 |
| e2e gate（loop-gate 1.1.1） | SessionStart 記下 HEAD；Stop 看改動量與驗證證據；Bash 的 `git commit`、`gh pr create` | observe，只記錄（2026-11-24 起，下個 session 生效） |
| check-skills-update | 排程 `CheckSkillsUpdate` 每週一 09:23；**錯過→下次開機登入後自動補跑**（StartWhenAvailable，2026-07-12 啟用） | Ready |
| skill 用量對帳 | 每次 Stop → `skill-usage\` | 運作中 |
| claude-mem 記憶同步 | SessionStart / Stop | 運作中 |
| harness 自動同步 | 每次 Stop（skills/、agents/、local-plugins/ 有變動）→ 自製秘鑰掃描，再過 gitleaks 第二層 → commit+push | 運作中；gitleaks 預設 observe，只記到 `hooks\harness-autosync.log`，環境變數 `HARNESS_GITLEAKS_MODE=enforce` 才擋。兩層都不吃 repo 裡的 `.gitattributes`，gitleaks 只用內建規則，`.gitleaks.toml`、`.gitleaksignore`、行內 `gitleaks:allow`、`GITLEAKS_*` 環境變數都放寬不了（2026-11-24） |
| harness-monthly-review | Claude App 排程，每月 1 日 09:30（App 要開著，bypass 權限模式） | 只出報告到 `audits\harness-monthly\<YYYY-MM>.md`：memory 整理建議、可刪的規則、`Verified: none` 的 commit、審查者命中率、觀察模式紀錄、主模型有沒有換 |
| Bedtime Hibernate | 系統匣常駐（開機自啟） | 1.1.0 |
| colonist watcher | 排程（未註冊，待手動 register-task.ps1） | 未啟用 |

## 歷史對照（2026-07-12 重構前的舊名）

| 舊 | 新 |
|---|---|
| GitHub `stan-claude-config` | GitHub `stan-claude-harness`（舊名自動轉址） |
| `Projects\stan-claude-config\`（傘狀容器） | 解散（暫存 `Projects\stan-claude-config.bak`，V6 驗證後刪） |
| `project-sweep-plugin` repo（GitHub 已封存） | `local-plugins\`（市集）；plugin `project-sweep`→`burn-credits`、`/sweep`→`/burn` |
| `claude-setup\`（drift sweep） | `ops\check-skills-update\`；排程 `ClaudeSetup-DriftSweep`→`CheckSkillsUpdate` |

## 維護慣例

- 新增/修改 hook：先用假 event JSON 餵 stdin 測過再啟用；壞了 `git checkout` 還原（validate-and-revert）。
- 改 hooks / plugin 設定要**重開 session** 才生效。
- 本 repo 是 **public**：push 前自檢 diff 有無敏感內容（memory/credentials 本來就不追蹤）。
- 在本 repo 內 commit 一律明確路徑 add，**嚴禁 `git add -A`**（會掃進 runtime 檔）。
- plugin 有變（新 plugin / 改版本）：bump version + CHANGELOG + commit（一功能一版號）。
- commit 前讀 `git show master:REVIEW.md`，查 diff 命中的項目；commit 訊息加一行 `Verified:` 寫怎麼驗的，沒驗寫 `none`。
- 新加會擋動作的 hook 或閘門先開觀察模式，看過誤擋再改成真的擋（e2e gate、gitleaks 都是這樣上線）。
- 在陌生 repo 開 session 前先跑 `py -I ~\.claude\scripts\inspect_repo.py <路徑>`。
- 升級 gitleaks 後要重驗 autosync 的第二層：它把掃描目標指到空資料夾、用 `GIT_DIR` 讀 staged 內容，靠的是 gitleaks 8.30.1 的內部行為，新版改了會悄悄變成 0 筆。
- humanizer 客製後記得 `git push backup main`。
- 這份 SETUP.md 與 memory 索引（`MEMORY.md`）分工：這裡記「東西在哪」，memory 記「事情做到哪」。
