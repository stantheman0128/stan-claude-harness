---
name: cross-model-handoff
description: Use when work crosses between Claude and Codex (OpenAI) — writing a brief to hand Codex, hardening a Codex-written prompt before running it here, or keeping AGENTS.md and CLAUDE.md from drifting into each other. Triggers on 交給 Codex / 派給 Codex / 叫 Codex 做 / hand this to Codex / Codex 寫的 prompt / AGENTS.md.
---

Claude and Codex are tuned to expect different prompt shapes. A brief that reads well for one degrades the other, and it fails in a named way each direction:

- Hand Codex a Claude-shaped brief and it **早停** — it treats "here is the plan" as a finishable turn and stops mid-rollout. OpenAI's own Codex guidance says to remove all prompting for upfront plans, preambles, and progress updates for exactly this reason.
- Hand Claude a Codex-shaped brief and it goes **字面** — Opus 4.8 and Sonnet 5 do not generalize an instruction across items and do not infer requests you didn't make, so Codex's deliberate leanness lands as under-specification.

Every rule below serves one of those two.

## Writing a brief for Codex

Four fields, all required, nothing else.

1. **Outcome** — what is true once this is done. Not the steps to get there. Codex's guidance is to describe the result and let it pick the approach.
2. **Anchor** — file paths, the failing test, the repro steps. Point at the code.
3. **Constraints** — what must not change. Permissions, public API, the branch it may not touch, the file it may not delete.
4. **Verification** — the command that proves it worked, and the output that counts as passing. Not optional. It is one of the four elements in OpenAI's own brief formula, and it is the field a Claude-trained habit most often drops.

Then strip these. They are normal here and they are 早停 bait over there:

- "First give me a plan" — Codex has `/plan` for that, in its own turn, not folded into a work brief
- Any instruction to narrate progress, emit a preamble, or check in mid-task
- Numbered step-by-step procedures — Codex is trained to bias to action, and a procedure invites it to stop after step one
- The same instruction said twice — OpenAI states each instruction once; a restatement reads as a new and possibly conflicting one

Last, a contradiction pass: no pair like "keep it brief" alongside "be exhaustive". GPT-5.x spends reasoning tokens reconciling conflicting instructions, so a contradiction is not merely ignored, it is billed.

**Done when** all four fields are filled, the strip list has zero hits, and no two instructions conflict.

## Hardening a Codex-written prompt

Codex writes lean because OpenAI tells it to. That leanness under-specifies for Opus 4.8. Add back:

- **Scope**, stated as a set. "Every section" beats "the section". Claude will not widen it on your behalf.
- **Intent** — why the task exists and who the output is for. OpenAI's guidance has no equivalent field, so a Codex-written brief will not carry one, and Claude uses it to connect the task to context it already holds.

**Done when** every instruction names the set it applies to, and the brief says why the work is being done.

This section is the fallback, not the plan. The fix belongs upstream: `~/.codex/skills/prompting-claude/SKILL.md` is the mirror of this skill, installed on the Codex side, and it tells Codex to supply scope and intent itself. If a Codex-written brief still arrives missing them, the mirror did not fire — say so, rather than silently patching it every time.

## AGENTS.md and CLAUDE.md

Same job, different readers, and they must not become the same file.

`AGENTS.md` is Codex's. Hard constraints and verification commands only. Lean is not a style preference here: OpenAI measured a leaner system prompt scoring 10 to 15% higher on their coding evals while spending 41 to 66% fewer tokens. Hard ceiling 32 KiB. Global file is `~/.codex/AGENTS.md`, then repo root, then per-directory, nearest wins.

`CLAUDE.md` is Claude's. Planning discipline, workflow routing, and progress-trace instructions live here and nowhere else. They are precisely what makes Codex 早停.

When a project needs one set of facts for both, put the facts in `AGENTS.md` and reduce `CLAUDE.md` to a pointer. `Projects/Nothing Phone Apps/line-notify/` already does this and is the reference implementation.

The sourced evidence behind every rule above, for when one is challenged, is in [`references/vendor-differences.md`](references/vendor-differences.md).
