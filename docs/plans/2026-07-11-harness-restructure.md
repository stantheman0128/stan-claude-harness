# Harness 重構執行計畫（stan-claude-harness 遷移 runbook）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把散在 `Projects\stan-claude-config\` 的自製工具併入 `~\.claude`，全面改名（stan-claude-harness / burn-credits / check-skills-update），並補齊 skills 備份完整性。

**Architecture:** 依 spec v2.1（`docs/specs/2026-07-11-harness-restructure-design.md`）。純遷移 runbook：每個 Task = 一組可獨立驗證的搬移/重接 + commit；驗證全用機器判定（V1-V8）；傘狀容器最後只改名 `.bak`，V6（重開 session 實測）過後才刪。

**Tech Stack:** git、gh CLI、schtasks、py（loop-gate scripts）。

## Global Constraints

- 執行位置：`C:\Users\stans\.claude`（harness repo）。所有 `git add` 用明確路徑。
- 每個 Task 結尾 commit（訊息照各 Task 指定），最後統一 push（T7 改名後的新 remote）。
- 舊傘狀容器內容只複製不刪改；`.bak` 改名放最後（T9）；刪除不在本計畫（V6 後另行）。
- 任何一步失敗：停下，`git checkout` 還原該步，回報，不硬推。
- schtasks 在 Git Bash 執行要 `MSYS2_ARG_CONV_EXCL="*"` 前綴防路徑轉換。

---

### Task 1: 前置安全檢查

- [ ] **Step 1**：`git -C C:/Users/stans/.claude status --porcelain` → 除已知 untracked（skills/commands 未追蹤者、overlays/、docs/plans 本檔）外無意外項；三個來源 repo `git status -sb` 全乾淨（project-sweep-plugin 與 origin 同步、claude-setup 無 remote 但乾淨、bedtime-hibernate 與 origin 同步）。
- [ ] **Step 2**：確認無其他 session 正在動 `Projects\stan-claude-config\`（詢問使用者或檢查近 5 分鐘 mtime）。

### Task 2: .gitignore 排雷（先於一切 add）

- [ ] **Step 1**：`~\.claude\.gitignore` 修改：
  - `plans/` → `/plans/`、`loop-gate/` → `/loop-gate/`、`backups/` → 保留原樣（全域匹配正好蓋住 ops 的 backups）、`paste-cache/`、`sessions/`、`todos/` 前加 `/` 錨定（同理防未來誤傷）。
  - 追加：
    ```
    # Restructure 2026-07-11
    skills/humanizer/
    skills/humanizer-zh-tw/
    ops/check-skills-update/reports/
    .claude/loop-gate-evidence.json
    local-plugins/**/__pycache__/
    .impeccable/
    ```
- [ ] **Step 2**：驗證：`git check-ignore -v local-plugins/loop-gate/x docs/plans/x` → 前者不得命中 `/loop-gate/`、後者不得命中 `/plans/`；`git check-ignore skills/humanizer/SKILL.md` 命中。
- [ ] **Step 3**：`git add .gitignore && git commit -m "chore: anchor runtime ignores + restructure ignore set"`

### Task 3: local-plugins 搬入 + burn-credits 改名

- [ ] **Step 1**：複製（不帶 .git）：
  ```bash
  U="C:/Users/stans/Projects/stan-claude-config/project-sweep-plugin"; H="C:/Users/stans/.claude"
  mkdir -p "$H/local-plugins"
  cp -r "$U/.claude-plugin" "$H/local-plugins/"
  cp -r "$U/sweep" "$H/local-plugins/burn-credits"
  cp -r "$U/loop-gate" "$H/local-plugins/loop-gate"
  cp -r "$U/docs/specs" "$U/docs/plans" "$H/docs/"   # loop-gate 的 spec/plan 併入
  ```
- [ ] **Step 2**：burn-credits 改名三件套：
  - `local-plugins/burn-credits/.claude-plugin/plugin.json`：name→`burn-credits`、version→`2.0.0`、description→"Burn remaining weekly usage limit: scan all projects for issues and batch-fix them"。
  - `commands/sweep.md` → 改名 `commands/burn.md`（指令 /burn）。
  - 新增 `local-plugins/burn-credits/CHANGELOG.md`：`## 2.0.0 - 2026-07-11\n- 更名 project-sweep → burn-credits（/sweep → /burn），遷入 stan-claude-harness/local-plugins。`
- [ ] **Step 3**：`local-plugins/.claude-plugin/marketplace.json` 重寫 plugins 陣列：
  `[{name: burn-credits, version: 2.0.0, source: ./burn-credits, description 同上}, {name: loop-gate, version: 1.0.1, source: ./loop-gate, description 原樣}]`
- [ ] **Step 4**：驗證：`claude plugin validate` 對 `local-plugins/burn-credits` 與 `local-plugins/loop-gate` 皆 pass；`py local-plugins/loop-gate/scripts/selftest/run.py` 18/18（V1、V2）。
- [ ] **Step 5**：`git add local-plugins docs/specs docs/plans && git commit -m "feat: local-plugins 市集遷入（burn-credits 2.0.0 更名 + loop-gate 1.0.1）"`

### Task 4: settings.json 重接

- [ ] **Step 1**：`extraKnownMarketplaces.stan-local-plugins.source.path` → `C:\Users\stans\.claude\local-plugins`；enabledPlugins 刪 `project-sweep@stan-local-plugins`、加 `"burn-credits@stan-local-plugins": true`。
- [ ] **Step 2**：`py -c "import json;json.load(open(r'C:/Users/stans/.claude/settings.json'))"` 無錯。
- [ ] **Step 3**：`git add settings.json && git commit -m "chore: marketplace 指向 local-plugins + burn-credits 啟用"`

### Task 5: loop-gate 信任表遷移 + dogfood manifest

- [ ] **Step 1**：寫 `~\.claude\.claude\verify.json`：`{"command": "py local-plugins/loop-gate/scripts/selftest/run.py", "timeoutSec": 180}`。
- [ ] **Step 2**：`py local-plugins/loop-gate/scripts/trust_manifest.py C:/Users/stans/.claude`；用 python 一行移除信任表舊 key `C:\Users\stans\Projects\stan-claude-config\project-sweep-plugin`。
- [ ] **Step 3**（V3）：在 `~\.claude` 用 `CLAUDE_PROJECT_DIR` 手動 pipe Stop event 打 `verify_gate.py` → 首跑 selftest 綠寫 evidence、二跑 0 秒放行。
- [ ] **Step 4**（V4）：同法對 `chrome-extensions` → 快路徑放行（不受影響）。
- [ ] **Step 5**：`git add .claude/verify.json && git commit -m "chore: loop-gate dogfood manifest 移至 harness root"`

### Task 6: ops\check-skills-update 搬入 + 排程重建

- [ ] **Step 1**：複製：`claude-setup/README.md → ops/check-skills-update/README.md`；`drift-sweep/ → ops/check-skills-update/check/`（bat 改名 `run-check.bat`）；`reports/ → ops/check-skills-update/reports/`（會被 gitignore，僅留磁碟）。
- [ ] **Step 2**：改 `run-check.bat` 內 3 處絕對路徑：`cd /d C:\Users\stans\.claude\ops\check-skills-update`、prompt 路徑 `...\ops\check-skills-update\check\prompt.md`、報告路徑 `...\ops\check-skills-update\reports\`。`grep -l "stan-claude-config" check/prompt.md README.md` 有命中則同步更新路徑。
- [ ] **Step 3**：排程刪舊建新：
  ```bash
  MSYS2_ARG_CONV_EXCL="*" schtasks /Delete /TN "ClaudeSetup-DriftSweep" /F
  MSYS2_ARG_CONV_EXCL="*" schtasks /Create /TN "CheckSkillsUpdate" /SC WEEKLY /D MON /ST 09:23 /TR "C:\Users\stans\.claude\ops\check-skills-update\check\run-check.bat"
  ```
- [ ] **Step 4**（V5）：`MSYS2_ARG_CONV_EXCL="*" schtasks /Query /TN "CheckSkillsUpdate" /V /FO LIST | grep -i "run-check"` 命中新路徑。
- [ ] **Step 5**：`git add ops/check-skills-update && git commit -m "feat: check-skills-update 遷入（原 claude-setup drift sweep）+ 排程重建"`（reports 被 ignore 屬預期）。

### Task 7: GitHub repo 改名 + 舊 plugin repo 封存 + push

- [ ] **Step 1**：`gh repo rename stan-claude-harness -R stantheman0128/stan-claude-config --yes`；`git -C C:/Users/stans/.claude remote set-url origin https://github.com/stantheman0128/stan-claude-harness.git`。
- [ ] **Step 2**：`gh repo edit stantheman0128/project-sweep-plugin --description "ARCHIVED 2026-07-11: moved into stan-claude-harness (local-plugins/, renamed burn-credits + loop-gate)"` 然後 `gh repo archive stantheman0128/project-sweep-plugin --yes`。
- [ ] **Step 3**：`git -C C:/Users/stans/.claude push origin master` 成功（推到新名 repo）。

### Task 8: humanizer 客製版備份（Stan 拍板：private backup remotes）

- [ ] **Step 1**：查兩支的 branch 名（`git -C skills/humanizer branch --show-current`，另一支同）。
- [ ] **Step 2**：`gh repo create stantheman0128/humanizer-stan --private -d "Stan's customized humanizer (v2.10.x, upstream=blader/humanizer)"`；`git -C skills/humanizer remote add backup https://github.com/stantheman0128/humanizer-stan.git`（已存在則 set-url）；`git push backup <branch>`。
- [ ] **Step 3**：同法 `humanizer-zh-tw-stan`（upstream=kevintsai1202/Humanizer-zh-TW）。
- [ ] **Step 4**：`gh repo view` 兩者 pushedAt 為今日。

### Task 9: skills/overlays 全量對帳（備份完整性）

- [ ] **Step 1**：`git add skills/ overlays/ commands/ agents/ hooks/ statusline.sh`（humanizer×2 已被 T2 gitignore 擋掉）。
- [ ] **Step 2**：`git status --porcelain` 檢視 staged 清單：確認 `skills/skill-routing/`、`skills/new-skill/`、`overlays/` 在內；無 `.git` gitlink（mode 160000）項。
- [ ] **Step 3**（V8 前半）：`git status --porcelain | grep -v '^A '` 應為空（除 SETUP.md/memory 等待 T10）。
- [ ] **Step 4**：`git commit -m "chore: skills/overlays 全量補進版控（skill-routing、new-skill 等 ~20 支）"`

### Task 10: bedtime-hibernate 搬回 + 傘狀容器 .bak

- [ ] **Step 1**：`mv "C:/Users/stans/Projects/stan-claude-config/bedtime-hibernate" "C:/Users/stans/Projects/bedtime-hibernate"`；`git -C .../bedtime-hibernate status -sb` 正常。
- [ ] **Step 2**：`mv "C:/Users/stans/Projects/stan-claude-config" "C:/Users/stans/Projects/stan-claude-config.bak"`（V6 過後另行刪除）。

### Task 11: 文件與記憶同步 + 最終驗收

- [ ] **Step 1**：重寫 `SETUP.md`：新 repo 名、新樹狀圖（local-plugins/burn-credits/loop-gate、ops/check-skills-update、overlays）、傘狀容器段刪除、humanizer 備份位置、維護慣例補「/burn 指令」「CheckSkillsUpdate 排程」。
- [ ] **Step 2**：memory 更新：`reference_claude_setup_map.md`（新名、傘狀容器已解散→.bak、humanizer 備份 repo）、`project_loop_gate.md`（新路徑、burn-credits）、MEMORY.md 兩行 hook 文字。
- [ ] **Step 3**（V8）：`git status --porcelain` 只剩刻意 ignore；`git add SETUP.md docs/plans/2026-07-11-harness-restructure.md && git commit -m "docs: SETUP.md 改版 + 重構計畫歸檔" && git push`。
- [ ] **Step 4**：向 Stan 回報 + 指示重開 session 做 V6（skill 清單見 burn-credits/loop-gate、實測一次收工 gate、`/burn` 指令存在）；V6 全綠後才刪 `.bak`。
