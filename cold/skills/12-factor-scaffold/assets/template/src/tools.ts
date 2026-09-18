import { z } from "zod";

/**
 * Factor 1 (natural language -> tool calls) + Factor 4 (tools are structured outputs):
 * Every LLM turn must produce exactly one of these shapes. A "tool call" is just
 * validated JSON; deterministic code decides what to do with it.
 *
 * request_human_input (factor 7) and done (factor 1) are tools too — no special paths.
 */
export const NextStepSchema = z.discriminatedUnion("intent", [
  z.object({ intent: z.literal("lookup"), query: z.string() }),
  z.object({ intent: z.literal("request_human_input"), question: z.string() }),
  z.object({ intent: z.literal("done"), final_answer: z.string() }),
]);
export type NextStep = z.infer<typeof NextStepSchema>;

/** Rendered into the prompt so the prompt and the parser never drift (factors 2, 4). */
export const TOOL_DESCRIPTIONS = `
- lookup(query: string): search the knowledge base.
- request_human_input(question: string): ask a human and pause.
- done(final_answer: string): finish with the answer.
`.trim();

/**
 * The only side-effecting tool. Side effects live in code, not in the schema.
 * Swap this mock for a real data source.
 */
export async function executeLookup(query: string): Promise<string> {
  return `knowledge-base result for "${query}"`;
}
