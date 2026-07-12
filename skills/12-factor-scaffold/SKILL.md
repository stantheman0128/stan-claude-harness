---
name: 12-factor-scaffold
description: Scaffold a new, runnable TypeScript AI agent that follows the 12-factor agents methodology. Use when the user wants to start a new agent project, asks for an agent starter/boilerplate/template, or says "create a new agent", "scaffold an agent", or "give me a 12-factor agent starter". Generates a project with an owned prompt, structured tool schema, a stateless-reducer loop, pause/resume, error caps, and an offline eval harness.
---

# 12-Factor Scaffold

> Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) by Dexter Horthy, adapted by tika/12-factor-agent-skills. Licensed CC BY-SA 4.0.

Generate a runnable TypeScript agent that bakes in the 12 factors. The starter runs **offline** (deterministic mock brain) so it builds and tests immediately, before any model is wired in.

## Generate a project

```bash
npx tsx scripts/scaffold.ts <target-dir> [--name <pkg-name>]
# example:
npx tsx scripts/scaffold.ts ./my-agent --name my-agent
```

Then:

```bash
cd <target-dir>
npm install
npm test        # eval harness for the stateless reducer (offline, no API key)
npm start       # run the example agent
npm run typecheck
```

## What it generates

A project where each factor has a home:

| File | Responsibility | Factors |
|------|----------------|---------|
| `src/state.ts` | One serializable state object | 5, 12 |
| `src/tools.ts` | Tool schema (discriminated union) + executors | 1, 4 |
| `src/prompt.ts` | Hand-written prompt + custom context renderer | 2, 3 |
| `src/llm.ts` | Injectable brain; validates output at the boundary | 1, 4 |
| `src/agent.ts` | Pure reducers + error compaction/cap | 9, 12 |
| `src/run.ts` | Owned control-flow loop; launch/pause/resume | 6, 8, 11 |
| `src/index.ts` | Example trigger (swap for Slack/HTTP/cron) | 11 |
| `test/agent.test.ts` | Eval harness: `(state, event) -> state` | 12 |

## After scaffolding

1. **Define the real tools** in `src/tools.ts` (the schema *is* the agent's capability surface).
2. **Wire a model** by replacing `mockBrain` with `createLLMBrain` in `src/llm.ts` — nothing else changes.
3. **Edit the prompt** in `src/prompt.ts` and bump `PROMPT_VERSION`.
4. **Add eval cases** in `test/agent.test.ts` for each new tool and edge case.

For design decisions before scaffolding, use **12-factor-design**. For factor definitions, see the **12-factor-agents** core skill.

## Notes

- Scripts run via `tsx` (bundled as a dev dependency in the generated project) or Node 23.6+.
- The generated agent has no network or API-key dependency until you plug in a real brain, so CI stays fast and deterministic.
