---
name: cross-model-handoff
description: Use when work crosses between Claude and Codex (OpenAI) — writing a brief to hand Codex, hardening a Codex-written prompt before running it here, or keeping AGENTS.md and CLAUDE.md from drifting into each other. Triggers on 交給 Codex / 派給 Codex / 叫 Codex 做 / hand this to Codex / Codex 寫的 prompt / AGENTS.md.
---

Claude and Codex are tuned to expect different prompt shapes. A brief that reads well for one degrades the other, and it fails in a named way each direction:

- Hand Codex a Claude-shaped brief and it **早停** — a plan delivered as an artifact is a finishable turn, so it stops before the work starts.
- Hand Claude a Codex-shaped brief and it goes **字面** — Opus 4.8 and Sonnet 5 do not generalize an instruction across items and do not infer requests you didn't make, so Codex's deliberate leanness lands as under-specification.

Every rule below serves one of those two.

## Writing a brief for Codex

Use OpenAI's own eight-section structure. Keep each section short; add detail only where it changes behavior.

| Section | What goes in it |
|---|---|
| Role | Who Codex is on this task |
| Personality | Only if tone matters. Usually one line or omitted |
| Goal | The destination, not the route |
| Success criteria | What must be true when done. Be concrete |
| Constraints | What must not change: permissions, public API, branches, files |
| Tools | Only the task-relevant ones. Say what each does, when to reach for it, and how it fails |
| Output | Shape and length. Codex has a `verbosity` parameter, so prefer setting that over prompting for length |
| Stop rules | When to stop and hand back, and what needs your confirmation first |

**Simplify before you add.** OpenAI measured leaner system prompts scoring roughly 10 to 15% higher on internal evals while cutting tokens 41 to 66% and cost 33 to 67%. The first pass is subtraction: cut repeated statements of the same rule, and cut examples that don't change behavior.

**Prefer decision criteria to absolutes.** Replace ALWAYS and NEVER with the judgment call itself: not "always run the tests", but "run the targeted tests for changed behavior; skip the full suite unless you touched shared code."

### The 早停 strip list

Cut these. They are habits from working here and they end Codex's turn early:

- **A plan as a deliverable.** "First give me a plan and I'll approve it" invites it to stop once the plan exists. Codex has `/plan` for that, as its own turn.
- **Narration of routine tool calls.** "Tell me each file as you read it."
- **Numbered step-by-step procedures.** Codex biases to action; a procedure invites it to stop after step one. Describe the destination and let it route.
- **The same instruction twice.** OpenAI states each instruction once; a restatement reads as a new and possibly conflicting rule, and contradictions burn reasoning tokens rather than being ignored.

What survives the strip list, and is in fact recommended for GPT-5.6: **a short preamble before the first tool call, then sparse updates at phase changes.** That is not a plan and not narration, and it does not trigger 早停.

**Don't raise `reasoning_effort` to paper over a bad brief.** OpenAI's guidance is explicit: before increasing effort, check whether the prompt is missing a success criterion, a dependency rule, a tool-routing rule, or a verification loop. Effort is the last lever, not the first.

**Done when** the eight sections are filled or consciously omitted, the strip list has zero hits, no two instructions conflict, and no ALWAYS/NEVER survives without a decision criterion behind it.

## Hardening a Codex-written prompt

Codex writes lean because OpenAI tells it to. That leanness under-specifies for Opus 4.8. Add back:

- **Scope**, stated as a set. "Every section" beats "the section". Claude will not widen it on your behalf.
- **Intent** — why the task exists and who the output is for. OpenAI's guidance has no equivalent field, so a Codex-written brief will not carry one.

**Done when** every instruction names the set it applies to, and the brief says why the work is being done.

This section is the fallback, not the plan. The fix belongs upstream: `~/.codex/skills/prompting-claude/SKILL.md` is the mirror of this skill, installed on the Codex side, and it tells Codex to supply scope and intent itself. If a Codex-written brief still arrives missing them, the mirror did not fire — say so, rather than silently patching it every time.

## AGENTS.md and CLAUDE.md

Same job, different readers, and they must not become the same file.

`AGENTS.md` is Codex's. Hard constraints and verification commands. Lean is not a style preference here, it is the measured result above. Hard ceiling 32 KiB. Global file is `~/.codex/AGENTS.md`, then repo root, then per-directory, nearest wins.

`CLAUDE.md` is Claude's. Planning discipline, workflow routing, and progress-trace instructions live here and nowhere else.

When a project needs one set of facts for both, put the facts in `AGENTS.md` and reduce `CLAUDE.md` to a pointer. `Projects/Nothing Phone Apps/line-notify/` already does this and is the reference implementation.

The sourced evidence behind every rule above, including the one place the two OpenAI documents contradict each other, is in [`references/vendor-differences.md`](references/vendor-differences.md).
