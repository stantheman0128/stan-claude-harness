---
name: oss-factory
description: >
  Stan 的多工具 OSS Contribution Factory（路徑 C:\Users\stans\Projects\oss）。
  主動使用當使用者要做開源貢獻、挖 issue、認領 claims、開 PR（stantheman0128）、
  與 Codex/Cursor/Grok 並行協作、更新 LEDGER/HANDOFF、加深 affinity repo、或提到
  claude-mem / hermes-agent / openclaw / OpenWhispr / neo / open-slide / toolhive。
  remotion 已 ban、OpenCC 已凍結勿碰。即使當前 cwd 不是 oss 也要用，一律改以工廠絕對路徑作業。
  Do not use 於私人產品（claude-mem-sync）、skill 蒸餾、yt-dlp、或 OpenCC。
user-invocable: true
---

# OSS Contribution Factory（Claude）

工廠根目錄（永遠用這個路徑，即使 workspace 在別處）：

`C:\Users\stans\Projects\oss`

## 開場必讀（依序）

1. `README.md`（短地圖）→ `AGENTS.md`
2. `HANDOFF.md`（**只讀最新 1–2 節**；不要讀 `handoff/archive/`）
3. `LEDGER.md`（最近列）
4. `claims/` 檔名（認領時再讀 `claims/README.md`）
5. `CANDIDATES.md`（`open` / `claimed` / `blocked`）
6. `FACTORY-TARGET.md`（目標 **100 merged|integrated**，不算 published）

## Session id

```text
claude-{yyyyMMdd-HHmmssfff}
```

例：`claude-20260718031600123`（含毫秒）。並行時幾乎不會撞號。同一 session 重跑沿用同一 id。

## 必做迴圈

0. **PR 輪迴（挖新票前）**：查 `stantheman0128` 的 open PR。優先：`CHANGES_REQUESTED`／未回的 maintainer 留言 → 真 CI 紅燈。在既有 fork 分支修並 push；更新 LEDGER／HANDOFF。若該 issue 的 claim 被別的 session 持有就換下一支。可做「只清 review」的 session。然後才挖新票。
1. Check 0：掃 `claims/`，已認領勿深想。
2. 備選 2–3 題（**優先 deepen** 已有 1 支 PR 的 affinity repo，不要先廣 scout）。
3. Check 1：原子認領

```powershell
cd C:\Users\stans\Projects\oss
.\claims\claim.ps1 -Owner <owner> -Repo <repo> -Issue <n> -Tool "Claude" -Branch "fix/<n>-<slug>" -Session "claude-<yyyyMMdd-HHmmssfff>"
```

exit 2 → 立刻換題。只有 `CLAIM_OK` 後才重現／寫碼。

4. `LEDGER.md` 加 `in-progress`。
5. 只在 `<repo>-wt/<item>/` 改碼。禁止寫 `FROZEN.md` 路徑與 `_archive/`。
6. Check 2：`claim.ps1 -VerifyOnly` + 串行 `gh` 查覆蓋 PR。
7. 品質閘見 `AGENTS.md`（AI 政策、HEAD 重現、測試、Evidence、Merge completeness bar）。**UI／設定頁／daemon：product-path Evidence 必備（arozos #289）。**
8. Check 3 後自行發佈（預設池 + Stan 點名授權的 repo）：fork `stantheman0128` → push → `gh pr create`（neo base=`dev`）。節流：每 repo ≤3 open、每天 ≤3 新 PR、間隔 ≥1h。
9. claim 補 `pr:`；LEDGER → `published`；收工用 handoff skill 寫 `HANDOFF.md` 一節。

## Deepen before scatter（2026-07-24）

scout 一波後：在最好的 1–2 個 affinity repo（Windows／zh-TW／台灣作者／日常 MCP）各做到 2–3 支高品質 PR，再等 review／merge；不要對十個新家各丟一支。加深目標例：`open-slide`、`toolhive`、`arozos`/`zoraxy`、`taiwan-md`（滿 3 open 就停）。

## @mention 與 case study

- 人類 @`stantheman0128`：**一律回覆**（ack + 立場）。既有 factory PR 的 standing autonomy 涵蓋這類回覆。
- 被 credit／fold-into／因超集關閉：當日追加 `handoff/CASE-STUDIES.md`（漏了什麼 + 下一題怎麼做滿）。見 `AGENTS.md` Merge completeness bar。

## CI triage

- Vercel「Authorization required」= maintainer 端，不是我們的程式債。
- CLA 歡迎留言可能簽完還掛著 → 看 check 狀態。
- Hermes `check-attribution` → `scripts/add_contributor.py <email> stantheman0128`，空 commit 重跑無效。

## S / M / L

- **S**：文件／設定／改名／清楚小 bug → **只做被邀請的 S**
- **M**：多檔、要仔細重現 → 正常做
- **L**：並發／狀態機／live repro → 強模型、一題一 session、對抗驗證

## 工廠總目標

`FACTORY-TARGET.md`：**100 merged**。本 session 只負責推進。達標數 LEDGER `merged|integrated` 或 `gh search prs --author stantheman0128 --merged --merged-at '>=2026-07-15'`。

## 預設可自行發 PR 的 repo

claude-mem、OpenWhispr、hermes-agent、openclaw（以及 Stan 當輪點名授權者）。issue/PR 留言另問。**禁止 yt-dlp、remotion。凍結 OpenCC。**
