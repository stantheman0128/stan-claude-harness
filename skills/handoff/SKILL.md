---
name: handoff
description: Session 交接記錄。主動使用本 skill 當使用者要收工、結束對話、下次想接續，或講「記錄一下」「寫 handoff」「收工」「下次繼續」「交接」「save progress」「/handoff」，即使沒明講。也在對話即將結束且本次做了實質工作時主動提出。產出一份結構化 HANDOFF.md（做了什麼/決策/狀態/已知問題/下一步/給下個 AI 的提示），任何 AI 工具都能讀來接手。寫前遮蔽 .env 等敏感資訊。Do not use for：持久化跨 session 記憶資料庫（用 claude-mem）、更新 CLAUDE.md（用 revise-claude-md）、git commit/PR。
---

# Session Handoff（工作交接記錄）

在 session 結束前，產出一份結構化的交接文件，讓下一個 session（不管是 Claude Code、Cursor、Copilot 或其他工具）都能無縫接手。

## 執行步驟

### 1. 回顧本次 session

掃描這次對話中的所有變更：
- 建立/修改/刪除了哪些檔案
- 做了哪些決策（以及為什麼）
- 遇到了什麼問題、怎麼解決的
- 還有什麼沒完成的

### 2. 產出 Handoff 文件

寫入專案根目錄的 `HANDOFF.md`（如果已存在則追加新的 session 記錄在最上面）。

格式如下：

```markdown
# Project Handoff

## Latest Session: [YYYY-MM-DD HH:MM]

### 做了什麼
- [具體的變更，每項一行]

### 關鍵決策
- [決策]：[為什麼這樣決定]

### 目前狀態
- 能跑嗎：[是/否/部分]
- 哪些功能完成了：[列表]
- 哪些還沒做：[列表]

### 已知問題
- [問題描述]（如果有的話）

### 下一步
1. [最優先要做的事]
2. [第二優先]
3. [第三優先]

### 給下一個 AI 的提示
- [任何重要的 context，例如「不要用 X 框架因為 Y」]
- [環境限制，例如「Windows 上要用 py 不是 python3」]

### 建議下個 AI 用的 skill
- [接手這份工作可能會用到的 skill，例如「改 Compose UI → chrisbanes」「逼問設計 → grilling」]

---

## Previous Session: [日期]
[之前的記錄保留在下面]
```

### 3. 確認位置

告訴使用者：「Handoff 已寫入 [路徑]/HANDOFF.md。下次開新 session 時，任何 AI 工具都可以讀這個檔案來接手。」

## 寫入規則

1. **用繁體中文**寫，但技術術語保留英文
2. **具體**：不寫「修改了一些檔案」，要寫「修改了 `src/server.ts` 的 route handler，加了 POST /api/notify endpoint」
3. **決策要附理由**：不寫「用了 SQLite」，要寫「用了 SQLite 因為不需要額外安裝，開發階段最簡單」
4. **下一步要可執行**：不寫「繼續開發」，要寫「實作 WebSocket 通知推送，參考 Phase 3 的 Slice 2」
5. **追加不覆蓋**：新 session 的記錄加在最上面，舊的保留。這樣能看到完整歷史
6. **遮蔽敏感資訊**：寫檔前移除 API key、密碼、token、PII（Stan 常貼 .env，這步別省）
7. **不複製其他文件**：已在 PRD / plan / ADR / commit / diff 記過的內容，用路徑或 URL 引用，別整段複製進來（避免過時副本）

## Handoff 檔案位置

- 如果在 git repo 裡 → 寫在 repo 根目錄
- 如果在桌面或沒有明確專案 → 寫在 `~/.claude/skill-data/handoff/latest.md`
- 使用者可以指定路徑
