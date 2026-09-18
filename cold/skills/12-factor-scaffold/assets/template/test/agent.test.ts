import { describe, it, expect } from "vitest";
import { initialState, serialize, deserialize, MAX_ERRORS, type State } from "../src/state";
import { applyDecision, applyEvent, compactError } from "../src/agent";
import { run, resume, checkpoint } from "../src/run";
import { renderContext } from "../src/prompt";

/**
 * Eval harness for the stateless reducer (factor 12): feed a state + event,
 * assert the next state. Because the reducers are pure, these tests are fast,
 * deterministic, and need no LLM or network.
 */

describe("pure reducers (factor 12)", () => {
  it("done decision sets status and final answer", () => {
    const s = initialState("goal");
    const next = applyDecision(s, { intent: "done", final_answer: "42" });
    expect(next.status).toBe("done");
    expect(next.finalAnswer).toBe("42");
  });

  it("request_human_input pauses the run (factors 6, 7)", () => {
    const next = applyDecision(initialState("goal"), { intent: "request_human_input", question: "ok?" });
    expect(next.status).toBe("awaiting_human");
  });

  it("caps consecutive errors then fails (factor 9)", () => {
    let s: State = initialState("goal");
    for (let i = 0; i < MAX_ERRORS; i++) s = applyEvent(s, { kind: "error", content: "boom" });
    expect(s.status).toBe("failed");
    expect(s.errorCount).toBe(MAX_ERRORS);
  });

  it("a successful event resets the error count (factor 9)", () => {
    let s = applyEvent(initialState("goal"), { kind: "error", content: "boom" });
    s = applyEvent(s, { kind: "tool_result", content: "ok" });
    expect(s.errorCount).toBe(0);
  });

  it("compacts errors to a short string (factor 9)", () => {
    expect(compactError(new Error("x".repeat(500))).length).toBeLessThan(230);
  });
});

describe("serialization (factors 5, 12)", () => {
  it("round-trips state", () => {
    const s = applyDecision(initialState("goal"), { intent: "lookup", query: "q" });
    expect(deserialize(serialize(s))).toEqual(s);
  });
});

describe("context rendering is pure (factor 3)", () => {
  it("renders a deterministic context string", () => {
    const ctx = renderContext(initialState("hello"));
    expect(ctx).toContain("<goal>hello</goal>");
    expect(ctx).toContain("1. user_request: hello");
  });
});

describe("end-to-end loop (offline, factors 8, 11)", () => {
  it("reaches done on a simple goal", async () => {
    const result = await run("What is the refund policy?");
    expect(result.status).toBe("done");
    expect(result.finalAnswer).toContain("knowledge-base result");
  });

  it("pauses for a human, then resumes to completion (factors 6, 7, 12)", async () => {
    const paused = await run("Confirm before deleting the account");
    expect(paused.status).toBe("awaiting_human");
    const resumed = await resume(checkpoint(paused), "yes");
    expect(resumed.status).toBe("done");
  });
});
