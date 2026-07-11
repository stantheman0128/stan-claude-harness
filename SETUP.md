# Stan Claude Harness — Setup 地圖

> 這份索引是「我的 Claude setup 有哪些東西、放在哪」的權威答案。
> 動過任何一塊就順手更新這裡。最後更新：2026-07-12（單一 repo 化重構完成）。

## 大原則：一個 repo

整個自建 harness ＝ 本資料夾 `~\.claude\` ＝ GitHub repo
**`stantheman0128/stan-claude-harness`**（public；原名 stan-claude-config，2026-07-12 改名）。
**push 一次＝全部備份完成**。唯二例外見「不進版控的東西」。

## 內容物

| 東西 | 路徑 | 說明 |
|---|---|---|
| 全域指令 | `CLAUDE.md` | 工作流規則：強制 skill 分流、pilotfish 分工制、透明 trace、humanizer 政策 |
| 設定 | `settings.json` | 權限、hooks 掛載、enabledPlugins、marketplace 指標（指向下面的 local-plugins） |
| 狀態列 | `statusline.sh` | 自製 statusline（context%、effort 顯示） |
| Hooks | `hooks\` | 11 支：skill 觸發系統 3 支＋規則檔、守門 2 支、session 中文名、claude-mem 5 支 |
| Agents | `agents\` | pilotfish 分工制：scout / mech-executor / executor / security-executor / verifier / quant-analyst |
| Skills | `skills\` | 37 資料夾（19 現役＋18 冷藏），**全量進版控**；humanizer×2 例外見下 |
| Overlays | `overlays\` | plugin overlay patch 檔（impeccable 5 條 harvest 等）——plugin 升版被蓋掉時的還原依據 |
| **自製 plugin 市集** | `local-plugins\` | marketplace 名 `stan-local-plugins`：**burn-credits** 2.0.0（`/burn` 掃全專案找問題批量修，燒剩餘額度；原名 project-sweep）＋ **loop-gate** 1.0.1（Stop hook 機器驗證 gate） |
| **運維** | `ops\check-skills-update\` | skill 上游更新檢查（原 claude-setup / drift sweep）：排程 `CheckSkillsUpdate` 每週一 09:23，雙篩自動收錄、四硬閘門、備份回滾 |
| 文件 | `docs\specs\`、`docs\plans\` | 設計 spec 與實作計畫（loop-gate、本次重構等） |

## 不進版控的東西（刻意）

| 東西 | 路徑 | 原因與備份方式 |
|---|---|---|
| 記憶 | `projects\C--Users-stans-Projects\memory\` | 含各專案細節，只留本機 |
| humanizer 客製版 | `skills\humanizer\`、`skills\humanizer-zh-tw\` | 各自是獨立 git repo（origin=上游，刻意 fetch 不 pull）；**備份 = private repos `humanizer-stan`、`humanizer-zh-tw-stan`（backup remote，客製後 `git push backup main`）** |
| 執行期狀態 | `/loop-gate\`、`hook-health.log`、`/jobs\`、`/security\`、`/skill-usage\` 等 | runtime，見 .gitignore |
| 休眠 app 安裝版 | `auto-hibernate\` | 可攜版有自己的 repo：`Projects\bedtime-hibernate`（GitHub public） |
| ops 的 reports/backups | `ops\check-skills-update\{reports,backups}\` | 產出物與回滾備份，只留本機 |

## loop-gate 速查（掛驗證 gate 的專案）

- 掛了 gate 的專案 = 有 `.claude\verify.json` 且經信任註冊者。目前：`chrome-extensions`、`~\.claude` 自身（dogfood：selftest 當 verify 命令）。
- 幫新專案掛：對 Claude 說「幫 X 專案掛驗證 gate」或「用 loop engineering 做」，或手動：
  寫 verify.json → `py ~\.claude\local-plugins\loop-gate\scripts\trust_manifest.py <專案根>`。
- 改 plugin 的 hook 前後跑 selftest：`py ~\.claude\local-plugins\loop-gate\scripts\selftest\run.py`（18 案例須全綠）。

## 自動化迴圈（會自己跑的東西）

| 迴圈 | 觸發 | 狀態 |
|---|---|---|
| loop-gate 驗證 gate | 每次 Stop（掛 manifest 的專案） | chrome-extensions + harness 自身 |
| check-skills-update | 排程 `CheckSkillsUpdate` 每週一 09:23 | Ready |
| skill 用量對帳 | 每次 Stop → `skill-usage\` | 運作中 |
| claude-mem 記憶同步 | SessionStart / Stop | 運作中 |
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
- humanizer 客製後記得 `git push backup main`。
- 這份 SETUP.md 與 memory 索引（`MEMORY.md`）分工：這裡記「東西在哪」，memory 記「事情做到哪」。
