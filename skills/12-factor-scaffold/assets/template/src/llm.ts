import type { State } from "./state";
import { NextStepSchema, type NextStep } from "./tools";
import { buildPrompt } from "./prompt";

/**
 * The "brain" is the only place the LLM lives. It is injectable so the agent loop
 * stays a pure, testable reducer (factor 12) and so you can run fully offline.
 */
export type Brain = (state: State) => Promise<unknown>;

/**
 * Factor 4: validate at the boundary. Whatever the brain returns MUST match the
 * schema before any code trusts it. A malformed output is an error to compact,
 * not a crash.
 */
export async function determineNextStep(state: State, brain: Brain): Promise<NextStep> {
  const raw = await brain(state);
  return NextStepSchema.parse(raw);
}

/**
 * Default offline brain: a deterministic policy so the starter runs with no API key.
 * Replace with createLLMBrain for real use.
 */
export const mockBrain: Brain = async (state) => {
  const askedHuman = state.events.some((e) => e.kind === "human_response");
  const needsHuman = /\b(confirm|approve|ask)\b/i.test(state.goal);
  if (needsHuman && !askedHuman) {
    return { intent: "request_human_input", question: `Please confirm the goal: ${state.goal}` };
  }
  const lastLookup = [...state.events].reverse().find((e) => e.kind === "tool_result");
  if (!lastLookup) {
    return { intent: "lookup", query: state.goal };
  }
  return { intent: "done", final_answer: `Based on lookup: ${lastLookup.content}` };
};

/**
 * Real LLM brain (factors 2, 3): builds the owned prompt + context, calls your model,
 * and returns parsed JSON. `complete` is your vendor call (OpenAI, Anthropic, AI SDK, ...).
 *
 * Example:
 *   const brain = createLLMBrain(async (prompt) => {
 *     const r = await openai.chat.completions.create({
 *       model: "gpt-4o", messages: [{ role: "user", content: prompt }],
 *       response_format: { type: "json_object" },
 *     });
 *     return r.choices[0].message.content!;
 *   });
 */
export function createLLMBrain(complete: (prompt: string) => Promise<string>): Brain {
  return async (state) => {
    const text = await complete(buildPrompt(state));
    return JSON.parse(text);
  };
}
