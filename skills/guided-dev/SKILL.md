---
name: guided-dev
description: 引導式開發全流程（spec、設計、切 slice、逐塊驗證、交付）。主動使用本 skill 當使用者要做需 3+ 步的功能、app 或新專案，講「幫我做」「幫我寫個」「開發」「build this」「implement」「做一個」「/guided-dev」，即使沒明講要走流程。本 skill 由 Claude 主導技術與架構決策、使用者只做產品決策，並內建自我挑戰與外部證據驗證。不要看到開發需求就直接動手，先用本 skill 判斷規模、設計、切 slice 再做。Do not use for trivial 1-2 file edits, or when the user explicitly wants only a plan/spec, only debugging, or only code review.
---

# Guided Development（引導式開發）

結合 Superpowers、5D、SPARC 和 Slice-Based 方法論的優點，為依賴 Claude 做技術決策的使用者設計。

**核心分工**：
- **你決定**：要做什麼、好不好、要不要
- **Claude 負責**：怎麼做、架構設計、品質把關、驗證

## Skill 資源

- `gotchas.md` — 開發過程常見問題（**每次開始前讀**）
- `references/verify-patterns.md` — Server/CLI/UI 各類驗證模式
- `references/debug-protocol.md` — 驗證失敗時的系統化排查步驟

---

## Phase 0: 判斷規模（5 秒）

先判斷任務大小，決定走哪條路：

| 規模 | 判斷標準 | 走哪條路 |
|------|---------|---------|
| **Trivial** | 1-2 個檔案、改動明確 | 直接做，不走流程 |
| **Small** | 3-5 個檔案、邏輯清楚 | 跳到 Phase 3（直接切 Slice） |
| **Medium** | 新功能、跨多個模組 | 從 Phase 1 開始 |
| **Large** | 新專案、新 app | 從 Phase 1 開始，Slice 數量 5+ |

---

## Phase 1: 理解（Research）

**目的**：搞清楚要做什麼、現有程式碼長什麼樣、技術上有什麼限制。

**Claude 的工作**：
1. 用 Explore subagent 研究現有程式碼、API、技術約束
2. 用 WebFetch/WebSearch 查閱需要的外部文件
3. 確認系統環境（工具版本、SDK、OS）

**問你的問題**（用簡單語言）：
- 「你想要這個東西做什麼？」（功能目標）
- 「誰會用它？怎麼用？」（使用場景）
- 「有沒有你已經在用的類似工具可以參考？」（參考對象）
- 「有沒有什麼一定不要的？」（排除項）

**不問你的問題**（Claude 自己決定）：
- 用什麼框架 / 語言 / 架構模式
- 資料庫結構 / API 設計
- 檔案結構 / 模組拆分

**產出**：技術約束清單 + 對需求的理解摘要。摘要給你確認：「我理解你要的是 X，對嗎？」

---

## Phase 2: 設計 + 挑戰（Design + Spar）

**目的**：設計架構，然後自己挑自己的毛病。

### 2a. 設計

用 Plan subagent 設計架構，考慮：
- 最簡單能 work 的方案（預設選這個）
- 是否有需要更複雜方案的理由
- **Seam-first**（取自 mattpocock to-spec，2026-07-14 harvest）：動手前先想清楚要在哪些接縫（seam）驗證這個功能，優先沿用既有接縫、用最高的接縫，接縫數量越少越好（理想＝1）。新接縫要提出來跟使用者確認符合預期，別悶頭多開

**給你看的不是技術細節，而是**：
- 「我打算這樣做：[用一句話說明方案]」
- 「這樣做的好處是：[1-2 點]」
- 「風險是：[如果有的話]」
- 「預計會建立 X 個檔案，分 Y 步完成」

### 2b. 自我挑戰（Spar）

> 靈感來自 5D methodology 的 Spar phase。

用 subagent 扮演挑戰者，檢查設計的盲區：
- 有沒有遺漏的 edge case？
- 有沒有更簡單的替代方案被忽略？
- 這個設計在使用者的環境（Windows、現有工具鏈）上能跑嗎？
- 有沒有安全性問題？

如果 Spar 發現重大問題 → 回到 2a 重新設計。
如果沒有重大問題 → 把發現的小問題記錄為 Slice 中的注意事項。

**給你確認**：「設計完成，我也自我挑戰過了。OK 開始做嗎？」

---

## Phase 3: 切 Slice（Slice Planning）

**目的**：把工作切成可獨立驗證的小塊。

### 切分原則

- 每個 Slice 產出**可運行、可測試的增量**
- 基礎設施（server、資料模型、設定檔）排前面
- UI / 整合排後面
- 每個 Slice 必須有：
  1. **範圍**：做什麼、不做什麼（3 行以內）
  2. **驗收標準**：一個具體的命令或操作來證明它 works
  3. **依賴**：哪些 Slice 要先完成

### Slice 大小

- 目標：每個 Slice 約 **2-5 分鐘**的工作量，或塞得進「一個全新 context window」（取自 mattpocock to-tickets，2026-07-14 harvest）
- 如果一個 Slice 感覺要 10+ 分鐘 → 再切
- **例外：大範圍機械性改動**（改欄名、重打共用 symbol 這種掃過整個 codebase、切不出能保持 CI 綠的垂直切片）→ 別硬切成 tracer bullet，改用 expand（新舊並存）→ migrate（按 blast radius 分批，每批被 expand 擋住）→ contract（刪舊，被所有 migrate 批次擋住）；批次自己也綠不了時，開一條共用 integration branch，全部擋住一張最終整合驗證 Slice（取自 mattpocock to-tickets，2026-07-14 harvest）

### 產出

用 TaskCreate 建立每個 Slice 為一個 Task。

---

## Phase 4: Build → Verify → Fix（每個 Slice）

這是核心迴圈。對每個 Slice：

### 4a. Build
- 寫程式碼（Write/Edit）
- 編譯（如果需要）
- 編譯失敗 → 立即修復，不進入 Verify

### 4b. Verify
- 根據驗收標準執行測試
- 驗證方式見 `references/verify-patterns.md`
- **關鍵**：用外部可觀察的證據，不是「我覺得應該對了」

### 4c. Fix（如果驗證失敗）
- 分析錯誤（見 `references/debug-protocol.md`）
- 修復 → 重新 Build → 重新 Verify
- **Re-plan 觸發條件**：
  - 同一個 Slice fix 超過 3 次 → 停下來重新評估 Slice 切分
  - 修復影響到已完成的 Slice → 回到 Phase 3 重新規劃
  - 發現原始設計有根本問題 → 回到 Phase 2

### 4d. 完成
- 驗證通過 → TaskUpdate 標記 completed
- 如果適合 → 建立 git commit

---

## Phase 5: 整合驗證（Integration Verify）

**所有 Slice 完成後**：

1. 模擬完整使用流程（不只是單一功能）
2. 測試邊界案例
3. 確認與現有系統的整合
4. 用 code-reviewer subagent 做最終品質檢查，**順便回頭核對 Phase 1 的需求摘要**：有沒有漏做的需求、有沒有做超出範圍的東西（scope creep）（取自 mattpocock code-review 的 spec-conformance 軸，2026-07-14 harvest）

**給你看**：
- 「全部完成。我測過了 [X, Y, Z] 場景，都通過。」
- 「有 N 個小問題，建議 [修 / 不修]」
- 最終的檔案清單和變更摘要

---

## Phase 6: 交付（Ship）

- 確認程式碼已 commit
- 如果需要：打包、push to GitHub、寫使用說明
- 清理暫存檔案

---

## 自動整合的 Skills

在適當的時機自動啟用：
- **Phase 1** → 考慮啟用 `/research-mode`（防止研究時意外改檔案）
- **Phase 5** → 考慮啟用 `/careful`（整合測試時防止危險操作）
- **Phase 5** → 如果是報告類產出，觸發 `report-verifier`

---

## 給 Claude 的提醒

1. **不要問使用者技術問題**。不要問「你想用 React 還是 Vue」「要用 REST 還是 GraphQL」。你來決定，用一句話解釋為什麼。
2. **用簡單語言解釋**。避免術語轟炸。如果必須用術語，加一句白話翻譯。
3. **每個 Phase 結束給一句話摘要**。讓使用者知道進度在哪。
4. **犯錯時直說**。「剛才的方案有問題，我改了，原因是 X」。不要掩蓋。
5. **Spar 要認真做**。不要走過場。真的去想「如果我是要挑毛病的人，我會怎麼攻擊這個設計」。
