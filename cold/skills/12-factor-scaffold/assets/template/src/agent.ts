import { type State, type AgentEvent, MAX_ERRORS } from "./state";
import { type NextStep, executeLookup } from "./tools";

/**
 * Pure reducers (factor 12). No IO here — given a state and something that happened,
 * compute the next state. These are what the eval harness tests.
 */

/** Apply the LLM's chosen step to state (records the decision, updates status). */
export function applyDecision(state: State, step: NextStep): State {
  switch (step.intent) {
    case "lookup":
      return {
        ...state,
        events: [...state.events, { kind: "tool_call", content: `lookup(${step.query})` }],
      };
    case "request_human_input":
      return {
        ...state,
        status: "awaiting_human", // factor 6/7: pause for a human
        events: [...state.events, { kind: "tool_call", content: `request_human_input(${step.question})` }],
      };
    case "done":
      return {
        ...state,
        status: "done",
        finalAnswer: step.final_answer,
        events: [...state.events, { kind: "tool_call", content: "done" }],
      };
    default: {
      const _exhaustive: never = step; // compile-time exhaustiveness (factor 4)
      return _exhaustive;
    }
  }
}

/** Fold a resulting event back into state. Factor 9: cap errors, then fail loudly. */
export function applyEvent(state: State, event: AgentEvent): State {
  if (event.kind === "error") {
    const errorCount = state.errorCount + 1;
    return {
      ...state,
      errorCount,
      status: errorCount >= MAX_ERRORS ? "failed" : state.status,
      events: [...state.events, event],
    };
  }
  return { ...state, errorCount: 0, events: [...state.events, event] };
}

/** Factor 9: compact an error into a short string the LLM can act on next turn. */
export function compactError(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  return `previous step failed: ${msg.slice(0, 200)}`;
}

/**
 * The only IO in the agent: execute a side-effecting tool. done and
 * request_human_input never reach here (the loop handles them via status).
 */
export async function executeStep(step: NextStep): Promise<AgentEvent> {
  switch (step.intent) {
    case "lookup":
      return { kind: "tool_result", content: await executeLookup(step.query) };
    case "request_human_input":
    case "done":
      throw new Error(`executeStep should not run for intent "${step.intent}"`);
    default: {
      const _exhaustive: never = step;
      return _exhaustive;
    }
  }
}
