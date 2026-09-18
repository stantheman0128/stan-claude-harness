---
name: 12-factor-agents
description: Knowledge base for the 12-factor agents methodology for building reliable production LLM agents (own your prompts, context, control flow, and state; tools as structured outputs; small focused agents; stateless reducers; human-in-the-loop). Use when the user asks about building reliable AI agents, mentions "12 factor agents", or needs the canonical explanation of any factor. For workflows, see the companion skills 12-factor-design, 12-factor-review, 12-factor-debug, and 12-factor-scaffold.
---

# 12-Factor Agents (Core)

> Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) by Dexter Horthy, adapted by tika/12-factor-agent-skills. Licensed CC BY-SA 4.0.

Principles for building LLM-powered software reliable enough for production customers. Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents). This is the **knowledge base**; the companion skills below apply it to concrete tasks.

## Core thesis

Good agents are **mostly deterministic software with LLM steps sprinkled in at the right points** — not "here's a prompt and a bag of tools, loop until done." Frameworks get you to ~70-80% quality fast, but the last 20% (what customers need) requires owning the prompts, context, and control flow yourself. Apply these factors as modular concepts inside existing software; you do not need a greenfield rewrite or an AI background.

The agent loop, reduced to its essence:

```python
context = [initial_event]
while True:
    next_step = await llm.determine_next_step(context)  # structured JSON
    context.append(next_step)
    if next_step.intent == "done":
        return next_step.final_answer
    result = await execute_step(next_step)               # deterministic code
    context.append(result)
```

## The 12 factors (quick reference)

1. **Natural language → tool calls** — Convert user intent into structured JSON tool calls; that's the agent's primary job.
2. **Own your prompts** — Treat prompts as first-class code you write and version, not hidden framework strings.
3. **Own your context window** — You control everything the LLM sees. Custom context formats > raw message arrays. Context engineering > prompt engineering.
4. **Tools are just structured outputs** — A tool call is just JSON the LLM emits; deterministic code decides what to do with it.
5. **Unify execution state and business state** — One source of truth; derive execution state from business state where possible.
6. **Launch / pause / resume with simple APIs** — Agents must start, pause for long work or humans, and resume cleanly.
7. **Contact humans with tool calls** — Asking a human is just another structured tool call, not a special control path.
8. **Own your control flow** — Write the loop, branching, and interrupts yourself. Don't cede control to the framework.
9. **Compact errors into the context window** — Summarize failures into context so the LLM self-heals; cap retries and escalate.
10. **Small, focused agents** — Prefer agents that own 3-10 steps; compose small agents rather than one mega-agent.
11. **Trigger from anywhere** — Launch from Slack, email, cron, webhooks, etc., and meet users in those channels.
12. **Stateless reducer** — Model the agent as `(state, event) -> new_state`. State lives outside; the agent is a pure function.

Bonus — **Factor 13: Pre-fetch context** — If you know you'll need data, fetch it deterministically up front.

Full factor-by-factor detail: [references/factors.md](references/factors.md).

## Companion skills

| Task | Skill |
|------|-------|
| Design a new agent against the factors | **12-factor-design** |
| Review / audit an existing agent (incl. `audit.ts` scanner) | **12-factor-review** |
| Debug an unreliable agent (symptom → factor) | **12-factor-debug** |
| Scaffold a runnable 12-factor TypeScript starter | **12-factor-scaffold** |

## Anti-patterns

- Reaching for a heavyweight framework before understanding the loop.
- Letting the LLM drive every decision when deterministic code would be more reliable.
- Unbounded agent loops with no error compaction or escalation (factor 9).
- Treating "agentic" as a goal in itself — the best products are mostly software with LLM steps at high-leverage points.

## Source

https://github.com/humanlayer/12-factor-agents (CC BY-SA 4.0)
