---
description: 全專案健檢與批量修復。掃描所有 git 專案、找出問題、討論後批量修復。適合用掉剩餘 weekly limit。
allowed-tools: [Agent, Bash, Read, Glob, Grep, Edit, Write, ToolSearch]
model: opus
---

# /sweep — 全專案健檢與批量修復

你是一個全專案掃描與修復工作流。用戶可能會說：
- `/sweep`
- `掃描所有專案`
- `用掉剩餘用量`
- `usage limit 還有 可以做什麼`
- `sweep all projects`

如果用戶附帶了參數 `$ARGUMENTS`，用它來過濾專案或指定模式（例如 `/sweep antnest-chatbot` 只掃描一個專案，`/sweep fast` 跳過討論直接修復）。

---

## Phase 1: 掃描（Scan）

### Step 1: 列出所有專案
```bash
for d in C:/Users/stans/Projects/*/; do
  if [ -d "$d/.git" ]; then
    echo "GIT: $(basename "$d")"
  fi
done
```

### Step 2: 檢查活躍度
對每個 git repo 跑：
```bash
git log --oneline -3 --format="%h %ad %s" --date=short
```
按最近提交日期排序。

### Step 3: 分類
- **活躍專案**（30 天內有 commit）→ 啟動 Explore subagent
- **休眠專案**（>30 天）→ 只列出名稱和最後日期，不深入

### Step 4: 平行探索
為每個活躍專案啟動一個 `subagent_type: "Explore"` agent，`run_in_background: true`。

每個 Explore agent 的任務模板：
```
Thoroughly explore the project at [PATH]. Report covering:
1. Project Overview (tech stack, purpose, deployment)
2. Current State (git log, branch, uncommitted changes)
3. Code Quality (TODOs, FIXMEs, console.logs, dead code, unused imports)
4. Potential Bugs (error handling gaps, edge cases)
5. What's Left To Do (TODO files, incomplete features)
6. Security Issues (.env leaks, npm audit, hardcoded secrets)
7. Dependencies (outdated/vulnerable packages)
Report in Traditional Chinese. Be structured and actionable.
```

---

## Phase 2: 報告（Report）

等所有 Explore agent 完成後，整理成報告：

### 報告格式
```markdown
# 全專案健檢報告

## 總覽儀表板
| 專案 | 活躍度 | 成熟度 | 安全風險 | 可快速修的問題數 |

## 各專案詳情
### [專案名]
**狀態**：...
**🔴 緊急問題**：...
**🟠 可改進**：...

## 建議行動優先級
### 🔴 立即處理（安全問題）
### 🟠 本週可做的清理
### 🟡 中期改進
```

### 討論環節
報告完成後，問用戶：
1. 哪些專案要修？
2. 哪些問題要處理？
3. 有沒有要跳過的？
4. 有沒有需要額外澄清的？

**如果用戶指定「fast」模式**，跳過討論，直接修復所有安全和品質問題。

---

## Phase 3: 修復（Fix）

根據用戶確認的範圍：

### 啟動修復 Agent
為每個要修的專案啟動一個 general-purpose agent：
- `isolation: "worktree"` — 在隔離分支上工作
- `run_in_background: true` — 平行執行
- 分支命名：`fix/sweep-YYYY-MM-DD`

### 修復範圍（選擇性）
- **安全修復**：`git rm --cached .env*`、確認 .gitignore、npm audit fix
- **代碼清理**：console.log 替換、dead code 移除、silent .catch 修復
- **型別改進**：any → proper types（只做最重要的 5-8 處）
- **文檔更新**：CLAUDE.md checklist、README 修正、版本號更新
- **依賴更新**：patch/minor version bumps（不做 breaking changes）

### 修復 Agent 指示
每個修復 agent 必須：
1. 在修改前先讀取相關文件
2. 修改後驗證建置成功（`npm run build` / `dotnet build` / 等效命令）
3. 建立清晰的 commit message（英文）
4. 不 push、不開 PR — 等用戶確認
5. 回報變更摘要（繁體中文）

---

## Phase 4: 回報（Summary）

所有修復完成後，給出最終摘要：

```markdown
## 修復完成摘要
| 專案 | 分支 | 變更內容 | 建置狀態 |

## 後續需要手動處理
- [ ] 密鑰輪換（列出平台）
- [ ] 需要 breaking change 的升級
- [ ] 需要用戶決策的項目
```

---

## 重要原則

- 所有溝通使用**繁體中文**
- **不主動 push 或開 PR** — 等用戶確認
- 修復只做**安全、品質、清理**類工作 — 不加新功能
- 尊重每個專案的 CLAUDE.md 規範
- 用 Explore agent 做探索、general-purpose agent 做修復
- 盡可能平行化 — 用 `run_in_background: true`
