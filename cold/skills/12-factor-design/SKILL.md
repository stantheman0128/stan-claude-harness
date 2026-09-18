---
name: 12-factor-design
description: Design a new AI agent or agentic feature against the 12-factor agents methodology. Use when the user wants to design, architect, or plan an LLM agent, asks "how should I structure my agent", is starting an agentic feature, or needs to decide where deterministic code should own the flow vs. the LLM. Produces a design that owns its prompts (factor 2), context (factor 3), tool schema (factor 4), control flow (factor 8), and state (factors 5, 12).
---

# 12-Factor Design

> Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) by Dexter Horthy, adapted by tika/12-factor-agent-skills. Licensed CC BY-SA 4.0.

Guide the design of a new agent so reliability is built in from the start. Pair with the **12-factor-agents** core skill for factor definitions ([../12-factor-agents/references/factors.md](../12-factor-agents/references/factors.md)).

## Principle

Decide up front **which decisions the LLM makes and which deterministic code makes**. Every step where code can decide reliably, let code decide. Reserve the LLM for genuine natural-language judgment. The output of design is a clear seam between the two.

## Design workflow

Work through these in order. Capture each as an explicit artifact, not a vibe.

```
- [ ] 1. Triggers & entry events    — where does this launch from? (factor 11)
- [ ] 2. Tool schema / outputs      — exact structured outputs the LLM may emit (factors 1, 4)
- [ ] 3. Prompt                     — hand-written, versioned (factor 2)
- [ ] 4. Context format             — what the LLM sees each turn, serialized (factor 3)
- [ ] 5. Control flow               — the loop + branch points; code vs LLM (factor 8)
- [ ] 6. State model                — one explicit, serializable object (factors 5, 12)
- [ ] 7. Pause/resume + human steps — long or risky steps (factors 6, 7)
- [ ] 8. Error policy               — compaction + retry cap + escalation (factor 9)
- [ ] 9. Scope check                — 3-10 steps; split if larger (factor 10)
- [ ] 10. Pre-fetch                 — known-needed data fetched deterministically (factor 13)
```

## Decision prompts

Ask these to force the important choices:

- **What is the smallest set of tools (structured outputs) that covers the goal?** Fewer, sharper tools beat many vague ones.
- **Where would a wrong LLM decision be expensive or irreversible?** Put a human-in-the-loop tool call there (factor 7).
- **What is the single state object?** If you can't serialize it to JSON and resume from it, redesign (factor 12).
- **Who owns the loop?** If the answer is "the framework," reclaim it (factor 8).
- **Is this one agent or several?** If it spans >10 steps or multiple domains, decompose (factor 10).

## Owned artifacts (copy these templates)

These are the three artifacts most teams accidentally cede to a framework. Own them from day one.

- **Prompt** (factor 2): [references/prompt-template.md](references/prompt-template.md)
- **Context format** (factor 3): [references/context-format.md](references/context-format.md)
- **Tool schema** (factor 4): [references/tool-schema.md](references/tool-schema.md)

## Output: design doc template

Produce a short doc the team can review before coding:

```markdown
# Agent: <name>

## Goal & non-goals
## Triggers (factor 11)
## Tools / structured outputs (factors 1, 4)   # list each: name, args schema, effect
## Prompt strategy (factor 2)                   # link to owned prompt
## Context format (factor 3)                    # what the LLM sees each turn
## Control flow (factor 8)                       # loop + branch points; code vs LLM seam
## State model (factors 5, 12)                   # the serializable state object
## Pause/resume & human-in-loop (factors 6, 7)
## Error & retry policy (factor 9)
## Scope & decomposition (factor 10)
## Pre-fetched context (factor 13)
```

When the design is ready, hand off to **12-factor-scaffold** to generate the runnable TypeScript starter.
