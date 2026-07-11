# Claude Code Setup 地圖

> 這份索引是「我的 Claude setup 到底有哪些東西、放在哪」的權威答案。
> 動過任何一塊就順手更新這裡。最後更新：2026-07-11。

## 中樞（本資料夾 `~\.claude\`，位置由 Claude Code 規定，不可搬）

| 東西 | 路徑 | 說明 |
|---|---|---|
| 全域指令 | `CLAUDE.md` | 工作流規則：強制 skill 分流、subagent 分工制、透明 trace、humanizer 政策 |
| 設定 | `settings.json` | 權限、hooks 掛載、enabledPlugins、marketplaces |
| 狀態列 | `statusline.sh` | 自製 statusline（含 context%、effort 顯示） |
| Hooks | `hooks\` | 11 支：skill 觸發系統（skill-suggest / skill-usage-log / skill-routing-watch）、守門（careful_guard / research_guard）、session 中文名（twify-session-name）、claude-mem 套件（5 支） |
| Agents | `agents\` | pilotfish 分工制：scout（唯讀偵察）、mech-executor（機械執行）、executor（判斷執行）、security-executor、verifier（對抗複驗）、quant-analyst |
| Skills | `skills\` | 30+ 支自製/收編 skill。**humanizer 與 humanizer-zh-tw 是獨立 git repo**（上游 clone + 本地 v2.10.0 客製，刻意不推） |
| 記憶 | `projects\C--Users-stans-Projects\memory\` | 跨 session 記憶（60+ 檔）。**刻意不進版控**（含各專案細節） |
| 休眠 app | `auto-hibernate\` | Bedtime Hibernate 安裝版（不進版控；可攜版見下方獨立 repo） |
| loop-gate 狀態 | `loop-gate\` + `hook-health.log` | 信任註冊表、strikes、工具失敗記錄、hook 健康 log（執行期狀態，不進版控） |

本資料夾的 git 備份：`github.com/stantheman0128/stan-claude-config`（**public**——
只追蹤 skills / commands / agents / hooks / settings / CLAUDE.md / statusline，
記憶、credentials、執行期狀態一律不追蹤。push 前自檢一眼 diff）。

## Projects 側（集中於傘狀容器 Projects\stan-claude-config\，2026-07-11 搬入；各自仍是獨立 git repo）

| 專案 | 路徑 | 是什麼 | 接點 |
|---|---|---|---|
| stan-local-plugins 市集 | `Projects\stan-claude-config\project-sweep-plugin\` | 自製 plugin 市集：**project-sweep**（全專案健檢）+ **loop-gate**（Stop hook 機器驗證 gate，2026-07-11） | `settings.json` 的 `extraKnownMarketplaces.stan-local-plugins`（directory）+ `enabledPlugins` |
| skill 體系運維 | `Projects\stan-claude-config\claude-setup\` | drift sweep 自動化 + 體系地圖（無 remote，只在本機） | 獨立運維專案 |
| Bedtime Hibernate 可攜版 | `Projects\stan-claude-config\bedtime-hibernate\` | 睡前一鍵→跑完自動休眠的公開版 | `github.com/stantheman0128/bedtime-hibernate` |

## loop-gate 速查（掛驗證 gate 的專案）

- 掛了 gate 的專案 = 有 `.claude\verify.json` 且經信任註冊者。目前：`chrome-extensions`、`project-sweep-plugin`。
- 幫新專案掛：對 Claude 說「幫 X 專案掛驗證 gate」（loop-engineering skill），或手動：
  寫 verify.json → `py Projects\stan-claude-config\project-sweep-plugin\loop-gate\scripts\trust_manifest.py <專案根>`。
- 改 plugin 的 hook 前後跑 selftest：`py Projects\stan-claude-config\project-sweep-plugin\loop-gate\scripts\selftest\run.py`（18 案例須全綠）。

## 附錄：逐項清單（2026-07-11 全面盤點）

### A. 自製/收編 Skills（`skills\`，37 資料夾 = 19 現役 + 18 冷藏）

**現役**：skill-routing（分流表+評估紀錄簿）、new-skill（工具評估流程）、guided-dev、
diagnosing-bugs、grilling、handoff、research-mode、security-audit、product-growth、
humanizer / humanizer-zh-tw（各為獨立 git repo，本地 v2.10.0）、transcribe、video-lens、
mineru、colonist-postmortem、cutting-demo-videos、write-like-joyce、prototype、writing-great-skills。

**冷藏**（`settings.json → skillOverrides: off`，還原=把該行刪掉）：adversarial-review、
analyze-forks、careful、codebase-design、context-compression、context-optimization、
domain-modeling、grill-me、memory-systems、mistral-ocr-tts、report-verifier、
setup-pre-commit、shadcn、to-issues、to-prd、triage、upstream-insights-report、video-lens-gallery。

### B. Commands（`commands\`，17 支，**全數冷藏**）

reels、new-task、adversarial-review、industry-report + api/×3 + misc/×6 + supabase/×2 + ui/×2。

### C. Agents（`agents\`，pilotfish 分工制）

scout（haiku 唯讀偵察）、mech-executor（規格化機械活）、executor（要判斷的實作）、
security-executor（安全敏感）、verifier（鎖寫入對抗複驗）、quant-analyst（量化專題）。

### D. Hooks（`hooks\` 11 支 + loop-gate plugin 3 支）

- skill 觸發系統：skill-suggest.py（UserPromptSubmit 關鍵字→提醒/🔒強制）、
  skill-usage-log.py（Stop，記真實載入供對帳）、skill-routing-watch.py（SessionStart）＋ skill-rules.json
- 守門：careful_guard.py（PreToolUse:Bash）、research_guard.py（PreToolUse 寫入類）
- session 中文名：twify-session-name.py（UserPromptSubmit+Stop）
- claude-mem 套件 5 支（SessionStart×3+Stop 同步）
- loop-gate（plugin 自帶）：verify_gate（Stop）、failure_log（PostToolUseFailure）、report_health（SessionStart）

### E. Plugins（12 個 marketplace、22 enabled）

自製：**project-sweep**、**loop-gate**（皆在 stan-local-plugins）。
主力第三方：superpowers、impeccable、agent-skills(addy)、claude-mem、hookify、ralph-loop、
document-skills、cloudflare、zeabur、github、context7、playwright、security-guidance、
兩個 output-style、5 個 LSP。已停用約 20 個（重複/殭屍，判準見 skill-routing EVALUATIONS）。

### F. 自動化迴圈（會自己跑的東西）

| 迴圈 | 觸發 | 狀態 |
|---|---|---|
| loop-gate 驗證 gate | 每次 Stop（掛 manifest 的專案） | 1.0.1，chrome-extensions + plugin repo 試點 |
| drift sweep（skill 上游同步） | 排程 `ClaudeSetup-DriftSweep` 每週一 09:23 | Ready（下次 2026-07-13） |
| skill 用量對帳 | 每次 Stop → `skill-usage\` | 運作中（57+ session logs） |
| claude-mem 記憶同步 | SessionStart / Stop | 運作中 |
| Bedtime Hibernate | 系統匣常駐（開機自啟） | 1.1.0 |
| colonist watcher | 排程（未註冊，待手動 register-task.ps1） | 未啟用 |

### G. MCP servers

大多由 Claude Desktop 連線層提供（Windows-MCP、github、computer-use、claude-in-chrome、
claude-mem search、visualize、preview 等），不在 settings.json 管理；
plugin 自帶的（cloudflare/context7/playwright 等）隨 plugin 開關。

## 維護慣例

- 新增/修改 hook：先用假 event JSON 餵 stdin 測過再啟用；壞了 `git checkout` 還原（validate-and-revert）。
- 改 hooks / plugin 設定要**重開 session** 才生效。
- plugin 市集有變（新 plugin / 改版本）：bump version + CHANGELOG + commit（一功能一版號）。
- 這份 SETUP.md 與 memory 索引（`MEMORY.md`）分工：這裡記「東西在哪」，memory 記「事情做到哪」。
