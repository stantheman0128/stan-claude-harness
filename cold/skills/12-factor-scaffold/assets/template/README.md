# __PROJECT_NAME__

A reliable LLM agent scaffolded from the [12-factor-agents](https://github.com/humanlayer/12-factor-agents) methodology. It runs **offline out of the box** (deterministic mock brain) so you can test the architecture before wiring a real model.

## Quick start

```bash
npm install
npm test        # eval harness for the stateless reducer (offline)
npm start       # run the example agent (offline)
npm run typecheck
```

## Architecture (where each factor lives)

| File | Responsibility | Factors |
|------|----------------|---------|
| `src/state.ts` | The one serializable state object | 5, 12 |
| `src/tools.ts` | Tool schema as a discriminated union + executors | 1, 4 |
| `src/prompt.ts` | Hand-written prompt + custom context renderer | 2, 3 |
| `src/llm.ts` | Injectable "brain"; validates output at the boundary | 1, 4 |
| `src/agent.ts` | Pure reducers + error compaction/cap | 9, 12 |
| `src/run.ts` | The control-flow loop; launch / pause / resume | 6, 8, 11 |
| `src/index.ts` | Example trigger (swap for Slack, HTTP, cron, ...) | 11 |
| `test/agent.test.ts` | Eval harness: `(state, event) -> state` | 12 |

## Plug in a real model

Replace the default `mockBrain` with `createLLMBrain` in `src/llm.ts`:

```ts
import OpenAI from "openai";
import { createLLMBrain } from "./llm";

const openai = new OpenAI();
const brain = createLLMBrain(async (prompt) => {
  const r = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: prompt }],
    response_format: { type: "json_object" },
  });
  return r.choices[0].message.content!;
});

const result = await run("your goal here", { brain });
```

The loop, state, tools, and tests don't change — only the brain does. That's the point of factors 8 and 12.
