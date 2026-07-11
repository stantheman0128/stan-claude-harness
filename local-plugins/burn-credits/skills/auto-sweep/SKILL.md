---
name: auto-sweep
description: >-
  Use this skill when the user mentions remaining usage limit, weekly limit resetting soon,
  wanting to use up remaining quota, or having spare capacity. Trigger phrases include:
  "usage limit", "weekly limit", "用量快到了", "用量還有剩", "limit 快重置",
  "還有額度", "剩餘用量", "burn remaining", "use up limit", "quota",
  "快要重製了", "limit還有", "趁還有用量", "把用量用完".
  When triggered, automatically invoke the /sweep command to scan all projects and batch-fix issues.
version: 1.0.0
---

# Auto-Sweep: 自動觸發全專案健檢

## 觸發條件

當用戶的訊息中包含以下意圖時，自動觸發此 skill：

- 提到 usage limit / weekly limit 快要重置
- 說還有剩餘用量想用掉
- 想要充分利用剩下的額度
- 問「還能做什麼」、「有什麼可以改進的」
- 說「趁還有時間」、「把用量用完」

## 行動

**立即使用 Skill 工具調用 `/sweep`。**

```
Skill({ skill: "sweep" })
```

如果用戶提到了特定專案或特定類型的問題，將該資訊作為參數傳遞：
- 提到特定專案 → `Skill({ skill: "sweep", args: "project-name" })`
- 說要快速處理 → `Skill({ skill: "sweep", args: "fast" })`

## 回應範例

用戶：「我 usage limit 還有 25% 快要重製了」
→ 回應：「好的，讓我啟動全專案掃描，把剩餘用量用在有價值的改進上。」
→ 調用 `/sweep`

用戶：「還有額度，有什麼能做的嗎」
→ 回應：「讓我掃描所有專案找可以改進的地方。」
→ 調用 `/sweep`

用戶：「快要重製了，幫我看一下 antnest-chatbot」
→ 回應：「好的，針對 antnest-chatbot 做健檢。」
→ 調用 `/sweep antnest-chatbot`
