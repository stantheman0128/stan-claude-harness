---
name: context-compression
description: Use when the user asks to "compress context", "summarize conversation history", "implement compaction", "reduce token usage", or mentions context compression, long-running agent sessions, or agents that "forget" previous steps.
---

# Context Compression Skill

## Core Insight

Optimize for **tokens-per-task**, not tokens-per-request. Aggressive compression that loses critical info causes re-fetching, which costs more overall.

## Three Production-Ready Approaches

| Method | Compression | Quality | Use When |
|--------|-------------|---------|----------|
| **Anchored Iterative** | 98.6% | Best (3.70) | Long sessions, file tracking matters |
| **Regenerative Summary** | 98.7% | Good (3.44) | Clear phase boundaries, readability needed |
| **Opaque** | 99.3% | Lowest (3.35) | Max savings, re-fetching cheap |

**Anchored Iterative is the default recommendation.** Structure forces preservation.

## Compression Trigger Strategies

| Strategy | Trigger | Trade-off |
|----------|---------|-----------|
| Fixed threshold | 70-80% context utilization | Simple |
| Sliding window | Keep last N turns + summary | Predictable size |
| Task-boundary | At logical task completions | Clean summaries |

## Structured Summary Template

```markdown
## Session Intent
[What the user is trying to accomplish]

## Files Modified
- file.ts: What changed and why

## Decisions Made
- Decision: Rationale

## Current State
- Tests: X passing, Y failing
- Blockers: None

## Next Steps
1. ...
```

## Probe-Based Quality Check

After compression, ask these questions — if the agent can answer correctly, compression preserved what matters:

| Probe | Question |
|-------|---------|
| Recall | "What was the original error message?" |
| Artifact | "Which files have we modified?" |
| Continuation | "What should we do next?" |
| Decision | "What did we decide about X?" |

## Anti-Patterns

- Compressing system prompts (never do this)
- Using tokens-per-request as the metric
- No separate tracking for artifact trail (files modified)
- Compressing too aggressively on first trigger

## Gotchas

### 1. 壓縮後丟失檔案路徑
- **問題**：壓縮摘要只寫「修改了幾個檔案」，沒有保留具體路徑和行號
- **正確做法**：Files Modified 區塊必須保留完整路徑，這是壓縮後最常被需要的資訊

### 2. 決策理由被壓掉
- **問題**：壓縮保留了「決定用方案 A」，但刪掉了「因為方案 B 有 X 問題」
- **正確做法**：Decisions Made 區塊必須包含 rationale，否則未來無法判斷決策是否仍然有效

### 3. 第一次觸發就壓太狠
- **問題**：context 到 70% 就觸發壓縮，一次壓掉 90%+ 的歷史
- **正確做法**：第一次壓縮保守一點（50-60% 壓縮率），後續再逐步加深。品質探針通過後才確認壓縮成功

### 4. 混淆壓縮與刪除
- **問題**：直接 truncate 舊 messages 而非 summarize
- **正確做法**：壓縮 = 用結構化摘要替換原始內容，不是直接丟掉

### 5. 壓縮後沒有驗證
- **問題**：壓縮完就繼續工作，不確認關鍵資訊是否保留
- **正確做法**：用 probe-based quality check（recall、artifact、continuation、decision 四個探針）驗證
