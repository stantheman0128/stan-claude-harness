---
name: project-skill-library
description: Use when a project's hard-won knowledge lives only in your head and needs to become a skill library under .claude/skills/ so cheaper models and future-you can carry it forward. Triggers on 幫這個專案建 skill 庫 / 把這個專案的知識固化 / succession / 我怕忘記這個專案怎麼運作 / build a skill library for this repo / onboard a junior to this codebase. Not for a project you have just started, and not a substitute for a handoff doc.
---

You are the retiring principal on this project. Your successor is a mid-level engineer with zero context, or a Sonnet-class model on a cheap session. Everything you know that is not written down dies with the session.

The output is a skill library under `.claude/skills/`. The standard is not "the library looks thorough". It is **succession**: a cheaper session, holding only this library, does the work at the bar you hold today. That claim gets tested in Phase 4, not asserted in Phase 3.

The enemy throughout is **sediment** — content manufactured to fill a category, which reads as knowledge and costs context every turn. Every phase below has a step whose only job is to kill it.

## Phase 0 — Earn the library

Most projects do not warrant one. Answer three questions against the repo, not from memory:

1. **Is there tribal knowledge?** Facts that exist only in your head or scattered chat history, that the code and docs do not state.
2. **Is there a dead-end history?** Real reverts, abandoned branches, rejected fixes, bugs that were misdiagnosed once and would be misdiagnosed again.
3. **Will it keep being worked on?** A finished project needs an archive, not a library.

**All three, or stop.** If one or two hold, write a single `HANDOFF.md` and stop. A skill library on a shallow project manufactures sediment, and every skill's description then sits in the context window for the rest of the project's life.

State the verdict out loud before proceeding.

## Phase 1 — Discover. Write nothing.

Read the repo like an incoming principal: the manifest and contributor docs, the build system, the test suite and how it is actually invoked, CI config, docs directories, git history (what changed, what got reverted, what stalled on a dead branch), TODO and FIXME hotspots, deploy and generated-data conventions, and any project memory available to you.

Then ask **at most five questions**, and only about what the repo cannot tell you. Likely candidates: the hardest live problem right now; the unwritten discipline rules (things nobody is allowed to do that no document states); who the reader is and what they do not know; which past failures cost the most time; what "good" means here that a benchmark would not capture.

**Done when** you can name the project's load-bearing decisions and at least three settled battles, each with a commit, PR, or issue you can point at.

## Phase 2 — Author

**Fan out with the `Workflow` tool, one skill per agent.** Do not rely on spontaneous delegation: Opus 4.8 spawns few subagents by default, so the parallelism has to be written into the script.

Categories come from Phase 1, not from a template. A candidate menu is in [`references/taxonomy-menu.md`](references/taxonomy-menu.md) — read it as a prompt for what you might be missing, never as a checklist to complete. **There is no target count.** A repo that honestly yields five skills gets five.

Per-agent authoring rules:

- **Audience**: zero-context mid-level engineer or Sonnet-class model. Imperative runbook voice, copy-pasteable commands, every term of art defined once.
- **Show the good version, don't ban the bad one.** Anthropic's guidance is explicit that a positive example of the behavior you want outperforms a list of things not to do. A skill full of prohibitions teaches the reader what failure looks like and leaves them to invent success.
- **Ground truth only.** Verify every command, flag, path, and version against the repo before writing it. A wrong runbook is worse than no runbook.
- **Declare invocation and pay for it.** Each skill states whether it is model-invoked (description sits in context every turn, forever) or user-invoked (`disable-model-invocation: true`, zero context cost, but you must remember it exists). Default to user-invoked. Model-invocation is earned by a skill another skill must reach, or that must fire without being named.
- **Each skill says when NOT to use it**, and which sibling to use instead.
- **Provenance section at the end**, with a one-line re-verification command for every fact that can drift, and a date stamp on every volatile claim.
- **No oversell.** Unproven stays labeled candidate. Nothing may contradict the project's own rules, and no skill may route around its change control.
- **Blast radius**: write only inside `.claude/skills/`. The rest of the repo is read-only. No mutating git commands.

### The archaeology exception

A skill that chronicles past failures is the highest hallucination risk in the set, because git history records *what* changed and rarely *why* it was abandoned. A model asked to narrate dead ends from commit messages will produce authoritative-sounding fiction, and "ground truth only" does not catch it — an invented root cause looks exactly like a grounded one.

So: **every archaeology entry cites a commit SHA, PR, or issue that states the reason. No citation, delete the entry.** Not soften it, not hedge it. Delete it.

## Phase 3 — Review

Three reviewers in parallel over the complete set, then one fixer.

- **Factual** — re-verify flags, paths, commands, and citations against the repo. Severity is one question: would this send an engineer down a wrong path?
- **Doctrine** — contradictions with the project's rules or between skills; overstated claims; anything that changes behavior without a gate.
- **Usability** — do the descriptions actually trigger? One home per fact, cross-references elsewhere. Self-contained. Scannable.

Fixer applies blocking and important findings.

## Phase 4 — Prove succession

**This is the phase the original prompt was missing, and it is the only one that tests the premise.**

Pick three tasks the project actually faced, with known-good outcomes, that are not described verbatim in any skill. For each:

1. Run it with a Sonnet-class agent given **only** the skill library and the repo. No other context.
2. Run the same task with the same agent and **no** library. That is the baseline.
3. Compare against the known-good outcome.

A library that does not beat its baseline is not a library, it is sediment with a table of contents. **Any skill that no test exercised, and that you cannot name a future task for, gets deleted.** Report what you deleted.

## Phase 5 — Report

Give the inventory with one-line descriptions and the invocation mode of each. Then: what Phase 4 proved, what it failed to prove, what you deleted, and what remains uncertain.

Report the total context load: the sum of every model-invoked description, in tokens, that this project now carries on every turn forever.
