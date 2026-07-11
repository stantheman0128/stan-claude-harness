# Harness 重構設計 spec（單一 repo 化 + 命名消歧）2026-07-11
# v2：Stan 命名拍板（stan-claude-harness / burn-credits / check-skills-update）+ skills 備份完整性納入範圍

## 動機：三個命名事故

1. **`stan-claude-config` 一詞兩義**：GitHub repo（`~\.claude` 的備份）與本機傘狀資料夾（`Projects\stan-claude-config\`，裝三個工具 repo）同名不同物。
2. **`sweep` 撞名**：project-sweep（掃「你的專案」找問題）與 drift sweep（掃「skill 的上游」找更新）是兩個完全不同的東西。
3. **名不符實**：repo 叫 `project-sweep-plugin` 卻住著兩個 plugin；資料夾叫 `claude-setup` 卻只管 skill 上游同步。

## 目標（方案一：真單一 repo）

自製 harness 工具全部併入 `~\.claude`，讓 GitHub 的 `stan-claude-config` 成為唯一的 repo：
**一個地方找東西、一次 push 完成全部備份、每個名字自我說明**。

### 佈局 Before → After

```
【Before】
~\.claude\                                  = repo stan-claude-config（public）
Projects\stan-claude-config\                = 傘狀資料夾（非 repo）
  ├─ project-sweep-plugin\                  = repo（private remote），內含 sweep\ + loop-gate\
  ├─ claude-setup\                          = repo（無 remote），drift-sweep 運維
  └─ bedtime-hibernate\                     = repo（public remote），獨立產品 app

【After】
~\.claude\                                  = repo stan-claude-harness（唯一的家；由 stan-claude-config 改名）
  ├─ CLAUDE.md / settings.json / statusline.sh / SETUP.md / docs\
  ├─ hooks\ / agents\ / commands\
  ├─ skills\                                ← skill-routing、new-skill 等全部在此，位置不動、全量進版控
  ├─ local-plugins\                         ← 自製 plugin 市集（marketplace 名仍為 stan-local-plugins）
  │   ├─ .claude-plugin\marketplace.json    （source 路徑改 ./burn-credits 與 ./loop-gate）
  │   ├─ burn-credits\                      ← 原 sweep\（plugin 與 skill 同步改名，指令 /burn）
  │   └─ loop-gate\
  ├─ ops\
  │   └─ check-skills-update\               ← 原 claude-setup（更名自我說明）
  │       ├─ check\（prompt.md、run-check.bat，原 drift-sweep\）
  │       ├─ reports\（gitignore）
  │       └─ backups\（gitignore）
  └─ overlays\                              ← plugin overlay patch 檔（若存在，必須追蹤）

Projects\bedtime-hibernate\                 ← 搬回 Projects 根（獨立產品，不屬 harness）
Projects\stan-claude-config\                ← 解散（驗證全綠後才刪，見回退計畫）
```

### 命名對照表（v2，Stan 2026-07-11 拍板）

| 舊名 | 新名 | 理由 |
|---|---|---|
| GitHub repo `stan-claude-config` | **`stan-claude-harness`**（`gh repo rename`，舊名自動轉址；本地 remote URL 同步更新） | 整包就是 Stan 自建的 harness |
| `Projects\stan-claude-config\`（資料夾） | （解散） | 消滅一詞兩義 |
| `project-sweep-plugin\`（repo） | `~\.claude\local-plugins\`（市集資料夾） | 名符其實：市集不是單一 plugin |
| plugin `project-sweep`（含 `sweep\` 資料夾與 `/sweep` skill） | **`burn-credits`**（資料夾、plugin 名、skill 名一致改為 burn → 指令變 `/burn`） | 它就是燒剩餘額度用的；順便消滅 sweep 撞名的一半 |
| plugin `loop-gate` | （不變） | Stan 拍板保留 |
| `claude-setup\`（drift sweep） | **`ops\check-skills-update\`**（排程任務同步改名 `CheckSkillsUpdate`） | 一看就懂：檢查 skills 上游更新；消滅 sweep 撞名另一半 |
| skill `skill-routing`、`new-skill` | （不變，Stan 拍板；本來就住 `skills\`，位置不動） | 名字直觀 |
| marketplace 名 `stan-local-plugins` | （不變） | 與內容正交；plugin 改名已要動 enabledPlugins，不再多動一層 |

注意：plugin 改名 `burn-credits` 需要連動 `enabledPlugins`：刪 `"project-sweep@stan-local-plugins"`、加 `"burn-credits@stan-local-plugins"`；marketplace.json 與 plugin.json 的 name 同步改。

### 備份完整性（v2 新增範圍——「我整個自建 harness 都要備份」）

1. **skills 全量對帳**：`skills\` 有 37 個資料夾但 repo 只追蹤 25 個檔案。執行時跑
   `git status` 全量盤點，把所有未追蹤的自製/收編 skill 檔案補進版控
   （執行期資料如 EVALUATIONS 的暫存另判）。skill-routing、new-skill 必須確認在內。
2. **humanizer / humanizer-zh-tw 例外處理**：兩支是獨立 git repo（remote=上游原作者），
   Stan 的 v2.10.0 客製 commit 目前**零備份**。它們不能直接 add 進 harness repo（巢狀 git 只會記
   gitlink）。**Stan 拍板（2026-07-11）**：各建一個 private GitHub repo（`humanizer-stan`、
   `humanizer-zh-tw-stan`）當 `backup` remote，push 本地 main；上游 fetch 工作流不受影響；
   harness repo 的 .gitignore 明列這兩個資料夾並在 SETUP.md 記載其備份位置。
3. **`overlays\` 目錄**（impeccable 的 5 條 harvest overlay 等 patch 檔）：確認存在則必須追蹤——
   這是 plugin 升版會被蓋掉時的唯一還原依據。
4. **agents / commands / hooks**：已於 2026-07-11 稍早補齊追蹤，執行時複驗一次全量。
5. **完整性驗收**：`git status --porcelain` 在 `~\.claude` 只剩「刻意 ignore」的項目
   （memory、credentials、執行期狀態、humanizer×2、plugin cache）。

## 搬移與連動重接（執行順序）

1. **前置快照**：`~\.claude` repo 先 commit 乾淨；確認無其他 session 正在動這些路徑。
2. **複製內容**（不帶 `.git`，避免巢狀 repo）：
   - `project-sweep-plugin\{sweep→burn-credits, loop-gate, .claude-plugin}` → `~\.claude\local-plugins\`
     （burn-credits 內 plugin.json 的 name、skill 資料夾與 SKILL.md 的 name 同步改為 burn-credits / burn）
   - `project-sweep-plugin\docs\{specs,plans}` → `~\.claude\docs\`（loop-gate 的 spec/plan 併入 harness docs）
   - `claude-setup\{README, drift-sweep→check, reports, backups}` → `~\.claude\ops\check-skills-update\`
   - `bedtime-hibernate\` → `Projects\bedtime-hibernate\`（整個 repo 原樣移動，含 .git）
3. **改 marketplace.json**：entry 改為 `burn-credits`（source `./burn-credits`）與 `loop-gate`（source `./loop-gate`）。
4. **改 settings.json 兩處**：(a) `extraKnownMarketplaces.stan-local-plugins.source.path`
   由 `C:\Users\stans\Projects\stan-claude-config\project-sweep-plugin` 改為 `C:\Users\stans\.claude\local-plugins`；
   (b) `enabledPlugins` 刪 `"project-sweep@stan-local-plugins"`、加 `"burn-credits@stan-local-plugins"`（loop-gate 那行不動）。
4b. **GitHub repo 改名**：`gh repo rename stan-claude-harness`（舊名 stan-claude-config 自動轉址）；
   本地 `git remote set-url origin https://github.com/stantheman0128/stan-claude-harness.git`。
4c. **skills 全量對帳**：盤點 `skills\` 未追蹤檔案全數補進版控（humanizer×2 除外，見備份完整性節）；
   確認 `overlays\` 存在與否並追蹤。
5. **loop-gate 信任表**：刪舊 key（`...Projects\stan-claude-config\project-sweep-plugin`）；
   dogfood manifest 移至 `~\.claude\.claude\verify.json`（root=`~\.claude`，command=`py local-plugins/loop-gate/scripts/selftest/run.py`），
   跑 `trust_manifest.py C:\Users\stans\.claude` 註冊。chrome-extensions 的信任項不動。
6. **skills 更新檢查排程**：檢查 bat 內部路徑並更新；舊任務 `ClaudeSetup-DriftSweep` 刪除、
   重建為 `CheckSkillsUpdate` 指向新 bat（schtasks 無改名，只能刪+建；Git Bash 下注意
   `MSYS2_ARG_CONV_EXCL` 路徑轉換雷）。
7. **.gitignore 增補**（`~\.claude`）：`ops/*/reports/`、`ops/*/backups/`、`local-plugins/**/__pycache__/`、`.claude/loop-gate-evidence.json`。
8. **文件與記憶**：SETUP.md 全面改路徑並刪傘狀容器段；memory 兩檔（reference-claude-setup-map、project-loop-gate）更新；傘狀容器 README 隨解散消失。
9. **舊 GitHub repo `project-sweep-plugin`（private）**：保留當歷史檔案庫，README 加一行「已遷移至 stan-claude-config/local-plugins（2026-07-11），此 repo 封存」。不合併 git 歷史（subtree 複雜度不值；15 個 commit 在舊 repo 永久可查）。
10. **分批 commit**（一步一 commit：local-plugins 搬入、ops 搬入、settings+信任、docs、SETUP.md）並 push。

## 驗證計畫（機器判定，全綠才算完）

| # | 驗證 | 通過標準 |
|---|---|---|
| V1 | `py ~\.claude\local-plugins\loop-gate\scripts\selftest\run.py` | 18/18 passed |
| V2 | `claude plugin validate ~\.claude\local-plugins\loop-gate`（與 burn-credits） | Validation passed |
| V3 | 手動 pipe Stop event 打 verify_gate（CLAUDE_PROJECT_DIR=`~\.claude`） | 首跑 selftest 綠→evidence；二跑 0 秒快路徑 |
| V4 | 同上但 CLAUDE_PROJECT_DIR=chrome-extensions | 快路徑放行（既有 evidence 仍有效，證明未受影響） |
| V5 | `schtasks /Query /TN "CheckSkillsUpdate" /V`（舊任務已刪） | TR 指向新 bat 路徑 |
| V8 | `~\.claude` 的 `git status --porcelain` 完整性驗收 | 只剩刻意 ignore 的項目；skill-routing / new-skill / overlays 確認已追蹤 |
| V6 | **重開 session 後**：skill 清單出現 `loop-gate:loop-engineering`、在掛 gate 專案實測一次收工 | plugin 從新路徑正常載入 |
| V7 | 舊傘狀資料夾刪除前 `git -C 各 repo status` | 無未 commit / 未 push 內容才准刪 |

## 回退計畫

- 傘狀資料夾在 V1-V6 全綠**之前**只改名為 `Projects\stan-claude-config.bak`，不刪除。
- `~\.claude` 的所有改動都是 commit 過的 → 任何一步壞掉 `git checkout` / `git revert` 即回。
- settings.json 路徑改壞的症狀 = 重開後 plugin 消失 → 把 path 改回 `.bak` 位置即恢復。

## 風險與已檢事項

- **public repo**：搬入的 plugin 與 ops 內容已做秘密掃描（無 token/金鑰）；drift-sweep 授權政策與 sweep 報告屬工作流描述，可公開。若改變主意：`gh repo edit --visibility private` 隨時可逆。
- **巢狀 git**：複製時明確排除 `.git`，並以 `git status` 確認新增檔案無 gitlink（mode 160000）。
- **多 session 並行**：執行窗口內其他 session 不得操作這些路徑（傘狀資料夾今天才由平行 session 建立，動手前再查一次 git status）。
- **claude-setup 的 2 個 commit 歷史將捨棄**（無 remote、內容已在 README 完整記載）；若要留，改為先推一份到 GitHub 封存（可選步驟，預設不做）。

## 明確不做（YAGNI）

合併舊 repo 的 git 歷史（subtree）、把 bedtime-hibernate 併入 harness、改 marketplace 名稱、
動第三方 plugins/skills 的任何位置、趁機清理冷藏 commands（另案）。

## 附錄：方案二（未採，備查）

不合併、只改名：`Projects\stan-claude-config\`→`claude-tools\`，`project-sweep-plugin`→`claude-plugins`（GitHub 同步改名）、`claude-setup`→`skill-upstream-sync`。歷史結構不動、風險最小，但「備份 repo + 工具容器」雙世界仍在。
