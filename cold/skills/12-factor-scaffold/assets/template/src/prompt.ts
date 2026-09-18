import type { State } from "./state";
import { TOOL_DESCRIPTIONS } from "./tools";

/**
 * Factor 2 (own your prompts): a hand-written, versioned prompt — not a hidden
 * framework string. Bump PROMPT_VERSION when you change it and log it per run.
 */
export const PROMPT_VERSION = "v1";

export const SYSTEM_PROMPT = `
You are a focused task agent. Your job is to achieve the goal using the available tools.

Rules:
- Respond with exactly one tool call as a single JSON object. No prose.
- Never invent data not present in the context.
- If you need information only a human can provide, call request_human_input.
- When the goal is achieved, call done with a final_answer.

Available tools:
${TOOL_DESCRIPTIONS}

Output contract: respond ONLY with one JSON object matching a tool schema.
`.trim();

/**
 * Factor 3 (own your context window): a custom, dense event-log format rather than
 * a raw chat array. You control exactly what the model sees each turn. This renderer
 * is pure, so it is unit-testable: given a state, assert the exact string.
 */
export function renderContext(state: State): string {
  const events = state.events
    .map((e, i) => `${i + 1}. ${e.kind}: ${e.content}`)
    .join("\n");
  return `<goal>${state.goal}</goal>\n\n<events>\n${events}\n</events>\n\nWhat is the next single tool call?`;
}

export function buildPrompt(state: State): string {
  return `${SYSTEM_PROMPT}\n\n${renderContext(state)}`;
}
