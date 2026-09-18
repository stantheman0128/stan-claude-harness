# The 12 Factors — Full Detail

Source: https://github.com/humanlayer/12-factor-agents (CC BY-SA 4.0). Read the relevant section before giving detailed advice on a factor.

## Factor 1: Natural Language to Tool Calls

The foundational move: convert a natural-language request into a structured, machine-readable tool call. Example: "create a $750 payment for Jeff" → `{"function": "create_payment_link", "amount": 750, "customer": "jeff"}`. Deterministic code takes that JSON and does the work. The LLM's job is intent → structured output; everything downstream is normal software.

## Factor 2: Own Your Prompts

Don't outsource your prompts to a framework's hidden templates. Once you need quality, you'll be reverse-engineering them anyway. Write prompts by hand, treat them as first-class code: version them, test them, and iterate. Prompts are the primary interface between you and the model — own that interface. Tools like BAML can help, but the principle is control.

## Factor 3: Own Your Context Window

You don't have to use the standard `[{role, content}, ...]` message format. The context window is the entire input to the LLM: system prompt, history, tool results, errors, retrieved data, memory. Engineer it deliberately — custom serialization formats can be denser and clearer than chat messages. This is "context engineering": maximize signal, minimize tokens, control exactly what the model sees at each step. This is often the single biggest lever on agent quality.

## Factor 4: Tools Are Just Structured Outputs

There is no magic in "tools." A tool call is just JSON the LLM produces. Your code parses it and decides what to do — call an API, update a DB, branch, or stop. Decoupling "the LLM emits structured output" from "code executes side effects" keeps the system testable and predictable. Tool definitions are just the schema of allowed outputs.

## Factor 5: Unify Execution State and Business State

Avoid maintaining two parallel worlds: "execution state" (current step, retry counts, pending calls) and "business state" (the actual domain data). Keep a single source of truth. Where possible, derive execution state from business state so there's nothing to get out of sync. Fewer state representations = fewer bugs and easier resumption.

## Factor 6: Launch / Pause / Resume with Simple APIs

Production agents must:
- **Launch** from a trigger (API call, event).
- **Pause** when waiting on a long-running tool, an external system, or a human — without holding a process open.
- **Resume** later from saved state, picking up exactly where it left off.

Implement these as simple, explicit APIs. This requires serializable state (see factors 5, 12).

## Factor 7: Contact Humans with Tool Calls

Human-in-the-loop is not a special escape hatch — it's just another tool. The LLM can emit `request_human_input` / `request_approval` like any other structured output, with a clear schema (question, options, urgency). Your control flow pauses (factor 6), routes to the human via the right channel (factor 11), and resumes with their response appended to context. This makes approvals, clarifications, and escalations first-class and uniform.

## Factor 8: Own Your Control Flow

The biggest one. Don't hand the loop to a framework that runs "think → act" until it decides it's done. Write the control flow yourself: you decide when to call the LLM, when to run deterministic code, when to branch, when to break out for an async task, and when to resume. Build interrupt/resume points. Owning control flow is what lets you add human approval, summarize errors, switch contexts, and enforce limits. Custom control structures (switch on the LLM's chosen tool, break out, loop back) beat a generic agent runtime.

## Factor 9: Compact Errors into the Context Window

When a tool call fails, don't dump a raw stack trace into context forever, and don't silently loop. Catch the error, **compact it into a concise message** the LLM can act on, and append it so the model can self-correct on the next turn. Cap the number of consecutive errors; after the cap, clear the error trail or escalate to a human (factor 7) rather than burning tokens in a failure loop. Self-healing within bounds is the goal.

## Factor 10: Small, Focused Agents

Resist the mega-agent. An agent that owns ~3-10 steps stays within a context length where the LLM performs reliably and stays easy to test and reason about. For bigger workflows, compose multiple small agents (or use deterministic orchestration between them) rather than one agent juggling 20+ steps. Even as models improve, smaller scope = higher reliability. Bound the blast radius of any single LLM decision.

## Factor 11: Trigger from Anywhere, Meet Users Where They Are

Decouple the trigger from the execution. Agents should launch from Slack, email, SMS, cron, webhooks, CLI, CI, or another agent — and respond in those same channels. This requires the launch/pause/resume APIs (factor 6) and stateless design (factor 12). Meeting users in their existing tools is often what makes an agent actually get adopted.

## Factor 12: Make Your Agent a Stateless Reducer

Model the agent as a pure function: `(state, event) -> new_state`, analogous to a Redux reducer. The agent holds no hidden internal state; all state is passed in and returned out, and persisted externally. Benefits: trivially resumable (factor 6), testable (feed a state + event, assert the output), debuggable (replay any state), and scalable (any worker can process the next event). This factor ties the others together.

## Factor 13 (Bonus): Pre-fetch All the Context You Might Need

If you already know the agent will need certain data, fetch it deterministically before invoking the LLM and put it in the context window — rather than spending an LLM turn (and a tool round-trip) to ask for it. Fewer turns, lower latency, fewer chances for the model to go off-track. Spend a deterministic call to save an LLM decision.
