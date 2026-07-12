import { z } from "zod";

/**
 * Factor 5 (unify state) + Factor 12 (stateless reducer):
 * One explicit, serializable state object is the single source of truth.
 * Everything the agent knows lives here; nothing hides in closures or globals.
 */

export const EventSchema = z.object({
  kind: z.enum(["user_request", "tool_call", "tool_result", "human_response", "error"]),
  content: z.string(),
});
export type AgentEvent = z.infer<typeof EventSchema>;

export const StateSchema = z.object({
  goal: z.string(),
  events: z.array(EventSchema),
  status: z.enum(["running", "awaiting_human", "done", "failed"]),
  finalAnswer: z.string().optional(),
  errorCount: z.number().int().nonnegative(),
});
export type State = z.infer<typeof StateSchema>;

/** Factor 9: cap consecutive failures instead of looping forever. */
export const MAX_ERRORS = 3;

export function initialState(goal: string): State {
  return {
    goal,
    events: [{ kind: "user_request", content: goal }],
    status: "running",
    errorCount: 0,
  };
}

/** Factor 12: state is serializable, so any run can be paused, stored, and replayed. */
export function serialize(state: State): string {
  return JSON.stringify(state);
}

export function deserialize(json: string): State {
  return StateSchema.parse(JSON.parse(json));
}
