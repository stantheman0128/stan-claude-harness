---
name: 12-factor-debug
description: Diagnose an unreliable or misbehaving AI agent by mapping symptoms to the 12 factors. Use when an agent loops forever, burns tokens, loses track of context, gives inconsistent outputs, can't resume, hallucinates tool calls, or is "stuck at 80%". Provides a symptom-to-factor lookup and a focused fix loop.
---

# 12-Factor Debug

> Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) by Dexter Horthy, adapted by tika/12-factor-agent-skills. Licensed CC BY-SA 4.0.

Turn a vague "the agent is unreliable" into a specific factor to fix. Factor definitions: [../12-factor-agents/references/factors.md](../12-factor-agents/references/factors.md). To scan the code first, use **12-factor-review**.

## Symptom → factor lookup

| Symptom | Likely factor | First fix |
|---------|---------------|-----------|
| Agent loops forever / burns tokens | 9, 8 | Add a retry/step cap; compact errors into context; escalate after N failures. |
| Loses the thread, forgets earlier steps | 3 | Curate/compact the context; stop dumping raw history. |
| Inconsistent or malformed outputs | 4, 2 | Validate outputs against a schema; tighten the owned prompt's output contract. |
| Makes the wrong decision at a key step | 3, 8 | Improve context first; move that decision to deterministic code if it shouldn't be the LLM's. |
| Hallucinates tools or arguments | 4, 2 | Constrain to a discriminated-union schema; list only real tools in the prompt. |
| Can't pause for a human / long task | 6, 7 | Add pause/resume APIs; make human contact a tool call. |
| Can't resume after a crash/restart | 12, 5, 6 | Make state a serializable object; rebuild from it. |
| Quality collapses on long tasks | 10, 3 | Split into smaller agents; shorten context. |
| Behaves differently every run | 12, 2 | Remove hidden state; pin prompt version; make the agent a pure reducer. |
| Can't reproduce a bad run | 12, 3 | Log the exact state + context; replay it. |
| Works in the demo UI, nowhere else | 11 | Decouple trigger from execution. |

## Fix loop

```
- [ ] 1. Reproduce: capture the exact input state + rendered context for one bad run.
- [ ] 2. Localize: map the symptom to a factor using the table above.
- [ ] 3. Inspect the context: print what the LLM actually saw that turn (factor 3 is the usual culprit).
- [ ] 4. Apply the smallest fix for that factor.
- [ ] 5. Replay the captured state and confirm the fix (this is easy iff you follow factor 12).
- [ ] 6. Add a regression test: state + event -> expected next_step.
```

## Debugging principle

**Print the context before blaming the model.** The single most common root cause is factor 3 — the LLM saw a bloated, stale, or under-specified context. Inspect the exact rendered input for the failing turn first; only then touch the prompt or model. If you can't easily capture and replay that input, your factor-12 design is the real bug.
