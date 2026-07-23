---
name: oss-factory
description: >
  Stan 的多工具 OSS Contribution Factory（路徑 C:\Users\stans\Projects\oss）。
  主動使用當使用者要做開源貢獻、挖 issue、認領 claims、開 PR（stantheman0128）、
  與 Codex/Cursor/Grok 並行協作、更新 LEDGER/HANDOFF、或提到 claude-mem / hermes-agent /
  openclaw / OpenWhispr / remotion / neo / Claude for OSS。OpenCC 已凍結勿碰。即使當前 cwd 不是 oss 也要用，
  一律改以工廠絕對路徑作業。Do not use 於私人產品（claude-mem-sync）、skill 蒸餾、yt-dlp、或 OpenCC。
user-invocable: true
---

# OSS Contribution Factory（Claude）

工廠根目錄（永遠用這個路徑，即使 workspace 在別處）：

`C:\Users\stans\Projects\oss`

## 開場必讀（依序）

1. `AGENTS.md`
2. `HANDOFF.md`（最新一節）
3. `LEDGER.md`
4. `claims/` + `claims/README.md`
5. `CANDIDATES.md`
6. 若存在：`FACTORY-TARGET.md`（工廠總目標進度）

## Session id

```text
claude-{yyyyMMdd-HHmmssfff}
```

例：`claude-20260718031600123`（含毫秒）。並行時幾乎不會撞號。同一 session 重跑沿用同一 id。

## 必做迴圈

0. **PR 輪迴（挖新票前）**：查 `stantheman0128` 的 open PR。優先：`CHANGES_REQUESTED`／未回的 maintainer 留言 → CI 紅燈。在既有 fork 分支修並 push；更新 LEDGER／HANDOFF。若該 issue 的 claim 被別的 session 持有就換下一支。可做「只清 review」的 session。然後才挖新票。
1. Check 0：掃 `claims/`，已認領勿深想。
2. 備選 2–3 題。
3. Check 1：原子認領

```powershell
cd C:\Users\stans\Projects\oss
.\claims\claim.ps1 -Owner <owner> -Repo <repo> -Issue <n> -Tool "Claude" -Branch "fix/<n>-<slug>" -Session "claude-<yyyyMMdd-HHmmssfff>"
```

exit 2 → 立刻換題。只有 `CLAIM_OK` 後才重現／寫碼。

4. `LEDGER.md` 加 `in-progress`。
5. 只在 `<repo>-wt/<item>/` 改碼。禁止寫 `FROZEN.md` 路徑與 `_archive/`。
6. Check 2：`claim.ps1 -VerifyOnly` + 串行 `gh` 查覆蓋 PR。
7. 品質閘見 `AGENTS.md`（AI 政策、HEAD 重現、測試、Evidence）。**M/L 另過「Merge completeness bar」**（同檔）：同一 state machine 的 race／persist／sibling 失敗要蓋滿，或明確寫進 What was not tested；被 credit／競合時 24h 內比 diff，擴到對等或讓路。**UI／設定頁／daemon 類 bug：Evidence 必須含 product path（截圖／跑起來的 API／實際 click-through），不可只有 helper unit test；若 What was not tested 就是使用者會看到的那條路，先補測再開 PR（arozos #289 教訓）。**
8. Check 3 後自行發佈（預設池）：fork `stantheman0128` → push → `gh pr create`（neo base=`dev`）。
9. claim 補 `pr:`；LEDGER → `published`；收工用 handoff skill 寫 `HANDOFF.md` 一節。

## S / M / L

- **S**：文件／設定／辭典／改名／清楚小 bug → 可快做
- **M**：多檔、要仔細重現 → 正常做
- **L**：並發／狀態機／live repro／難查根因 → 強模型、一題一 session、對抗驗證

## 工廠總目標（例如 100）

若 `FACTORY-TARGET.md` 有目標（如 100 筆新 published/merged）：本 session **不負責一個人做完**，只負責推進並在收工時更新進度計數。達標判定以 LEDGER 為準，不是 claims 檔案數（claims 會刪）。

## 預設可自行發 PR 的 repo

claude-mem、OpenWhispr、remotion、hermes-agent、openclaw。issue/PR 留言另問。禁止 yt-dlp。**凍結：BYVoid/OpenCC**（勿 scout／claim／開 PR）。
