# Owned Context Format (Factor 3)

The context window is the entire input to the LLM. You do not have to use the standard `[{role, content}, ...]` array — a custom, dense format is often clearer and cheaper. Engineer exactly what the model sees each turn.

## A custom event-log format

Render your state as a compact, readable event log rather than chat turns:

```
<goal>Refund order #1234 if eligible, otherwise explain why.</goal>

<events>
1. user_request: "I want a refund for order 1234"
2. tool_call get_order(id=1234)
3. tool_result get_order: {status: "delivered", total: 49.99, age_days: 12}
4. tool_call check_refund_policy(age_days=12, status="delivered")
5. tool_result check_refund_policy: {eligible: true, max_refund: 49.99}
</events>

<available_tools>create_refund, request_human_input, done</available_tools>

What is the next single tool call?
```

## What to include (and not)

- **Include:** the goal, the relevant event history, tool results, pre-fetched data (factor 13), and any compacted error (factor 9).
- **Compact aggressively:** summarize old/verbose tool results; keep recent turns verbatim. Long raw context degrades reliability and is the most common cause of bad agent decisions.
- **Exclude:** anything the model doesn't need this turn. Token budget is shared.

## Why a custom format

- Denser than chat messages → more signal per token.
- Deterministic serialization from your state object → reproducible runs (factor 12).
- You can unit-test the renderer: given a state, assert the exact context string.

## Rule of thumb

If agent quality is poor, audit the context **before** touching the prompt. Context engineering is usually the bigger lever.
