---
name: context-optimization
description: Use when the user asks to "optimize context", "reduce token costs", "improve context efficiency", "implement KV-cache optimization", "implement prompt caching", or discusses context limits, observation masking, context budgeting, or extending effective context capacity.
---

# Context Optimization Skill

## Four Primary Optimization Strategies

1. **Compaction** — Summarizing context contents when approaching limits, targeting 50-70% token reduction with minimal quality loss

2. **Observation Masking** — Replacing verbose tool outputs with compact references, achieving 60-80% reduction in masked observations

3. **KV-Cache Optimization** — Reusing cached Key-Value tensors across requests sharing identical prefixes, targeting 70%+ hit rates. For Claude API: use `cache_control: {type: "ephemeral"}` on stable content (system prompts, knowledge bases). Cache TTL is 5 minutes; costs 25% of base write price, reads cost 10%.

4. **Context Partitioning** — Distributing work across isolated sub-agent contexts for separation of concerns

## Key Implementation Insights

"Context quality matters more than quantity." Tool outputs often comprise 80%+ of agent trajectory tokens — observation masking is most impactful after decisions are made.

Compaction priority order: tool outputs → old conversational turns → retrieved documents (protect system prompts from compression).

Cache optimization: position stable elements (system prompts, tool definitions, knowledge bases) **before** dynamic content to maximize prefix reuse.

## Activation Triggers

Apply when:
- Context utilization exceeds 70%
- Response quality degrades with conversation length
- Costs rising due to large, repeated context (e.g. large system prompt sent every turn)

## Gotchas

### 1. Cache TTL 過期沒處理
- **問題**：以為 cache 一直在，但 Anthropic prompt cache TTL 只有 5 分鐘。超過後重新計費
- **正確做法**：高頻對話（<5 min 間隔）才值得 cache。低頻場景反而多花 25% write cost

### 2. 動態內容放在 cache 區塊前面
- **問題**：把變動頻繁的 user context 放在 system prompt 前面，導致每次都 cache miss
- **正確做法**：穩定內容（system prompt、工具定義、知識庫）放前面，動態內容放後面

### 3. Observation masking 太早
- **問題**：tool output 還沒被用於決策就被 mask 掉了
- **正確做法**：只在 agent 已經基於 output 做出決策後才 mask。Mask 時保留決策結果

### 4. 以為 KV-cache 能跨 session
- **問題**：期望上一個 session 的 cache 在新 session 還有效
- **正確做法**：KV-cache 是 request 級別的，只在同一 session 的連續請求間有效

## Prompt Caching Example (Anthropic API)

```python
client.messages.create(
    model="claude-sonnet-4-6",
    system=[
        {
            "type": "text",
            "text": "<large knowledge base here>",
            "cache_control": {"type": "ephemeral"}  # cache this block
        }
    ],
    messages=[{"role": "user", "content": user_message}]
)
```

Cache the static knowledge base once; only the user message changes each turn. Cost drops ~90% on cached tokens after first request.
