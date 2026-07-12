import { type State, initialState, deserialize, serialize } from "./state";
import { type Brain, mockBrain, determineNextStep } from "./llm";
import { applyDecision, applyEvent, compactError, executeStep } from "./agent";

/**
 * Factor 8 (own your control flow): the loop is written here, by you — not delegated
 * to a framework. Factor 6 (launch/pause/resume) + Factor 11 (trigger from anywhere):
 * run() and resume() are plain functions any trigger can call.
 */

export interface RunOptions {
  brain?: Brain;
  maxTurns?: number;
}

/** Launch a new run from a goal. */
export async function run(goal: string, opts: RunOptions = {}): Promise<State> {
  return loop(initialState(goal), opts);
}

/** Resume a paused run (e.g. after a human answered). Rebuilt purely from saved state. */
export async function resume(serializedState: string, humanResponse: string, opts: RunOptions = {}): Promise<State> {
  let state = deserialize(serializedState);
  state = applyEvent(state, { kind: "human_response", content: humanResponse });
  state = { ...state, status: "running" };
  return loop(state, opts);
}

async function loop(start: State, { brain = mockBrain, maxTurns = 10 }: RunOptions): Promise<State> {
  let state = start;
  for (let turn = 0; turn < maxTurns && state.status === "running"; turn++) {
    let step;
    try {
      step = await determineNextStep(state, brain);
    } catch (err) {
      state = applyEvent(state, { kind: "error", content: compactError(err) }); // factor 9
      continue;
    }

    state = applyDecision(state, step);
    if (state.status !== "running") break; // done or awaiting_human — pause here (factor 6)

    try {
      state = applyEvent(state, await executeStep(step));
    } catch (err) {
      state = applyEvent(state, { kind: "error", content: compactError(err) });
    }
  }
  return state;
}

/** Persist a paused run so a different process/worker can resume it (factors 6, 12). */
export function checkpoint(state: State): string {
  return serialize(state);
}
