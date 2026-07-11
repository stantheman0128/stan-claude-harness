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

## Projects 側（原始碼住外面、由 settings.json 指標接進來）

| 專案 | 路徑 | 是什麼 | 接點 |
|---|---|---|---|
| stan-local-plugins 市集 | `Projects\project-sweep-plugin\` | 自製 plugin 市集：**project-sweep**（全專案健檢）+ **loop-gate**（Stop hook 機器驗證 gate，2026-07-11） | `settings.json` 的 `extraKnownMarketplaces.stan-local-plugins`（directory）+ `enabledPlugins` |
| skill 體系運維 | `Projects\claude-setup\` | drift sweep 自動化 + 體系地圖（無 remote，只在本機） | 獨立運維專案 |
| Bedtime Hibernate 可攜版 | `Projects\bedtime-hibernate\` | 睡前一鍵→跑完自動休眠的公開版 | `github.com/stantheman0128/bedtime-hibernate` |

## loop-gate 速查（掛驗證 gate 的專案）

- 掛了 gate 的專案 = 有 `.claude\verify.json` 且經信任註冊者。目前：`chrome-extensions`、`project-sweep-plugin`。
- 幫新專案掛：對 Claude 說「幫 X 專案掛驗證 gate」（loop-engineering skill），或手動：
  寫 verify.json → `py Projects\project-sweep-plugin\loop-gate\scripts\trust_manifest.py <專案根>`。
- 改 plugin 的 hook 前後跑 selftest：`py Projects\project-sweep-plugin\loop-gate\scripts\selftest\run.py`（18 案例須全綠）。

## 維護慣例

- 新增/修改 hook：先用假 event JSON 餵 stdin 測過再啟用；壞了 `git checkout` 還原（validate-and-revert）。
- 改 hooks / plugin 設定要**重開 session** 才生效。
- plugin 市集有變（新 plugin / 改版本）：bump version + CHANGELOG + commit（一功能一版號）。
- 這份 SETUP.md 與 memory 索引（`MEMORY.md`）分工：這裡記「東西在哪」，memory 記「事情做到哪」。
