# Tool Schema = Structured Outputs (Factor 4)

A "tool" is not magic. It is a named JSON shape the LLM is allowed to emit. Your deterministic code parses that JSON and decides what to do — including doing nothing, branching, or stopping. Define tools as a discriminated union of structured outputs.

## TypeScript pattern

```ts
// Every LLM turn must produce exactly one of these.
export type NextStep =
  | { intent: "get_order"; order_id: number }
  | { intent: "create_refund"; order_id: number; amount: number }
  | { intent: "request_human_input"; question: string; options?: string[] }
  | { intent: "done"; final_answer: string };

// Validate at the boundary (e.g. with zod) before trusting it.
```

## Principles

- **Discriminated union on `intent`** makes the LLM output exhaustively handleable in a `switch` (this is your control flow, factor 8).
- **Validate every output** against the schema before executing. A malformed output is an error to compact (factor 9), not a crash.
- **Side effects live in code, not in the schema.** The schema only describes *what the model wants*; an executor decides whether and how to do it.
- **Keep the set small and orthogonal.** Overlapping tools confuse the model. Prefer 3-10 sharp tools (relates to factor 10).
- **`request_human_input` and `done` are tools too** (factors 7, 1) — no special control paths.

## Executor sketch

```ts
async function execute(step: NextStep, state: State): Promise<State> {
  switch (step.intent) {
    case "get_order":            return appendResult(state, await getOrder(step.order_id));
    case "create_refund":        return appendResult(state, await createRefund(step.order_id, step.amount));
    case "request_human_input":  return pauseForHuman(state, step);   // factor 6/7
    case "done":                 return finish(state, step.final_answer);
    default: {
      const _exhaustive: never = step; // compile-time exhaustiveness
      return _exhaustive;
    }
  }
}
```

Generate the prompt's tool list directly from this schema so the prompt and the parser never drift.
