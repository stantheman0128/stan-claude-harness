# Vendor differences: Anthropic vs OpenAI

Sourced backing for the rules in `SKILL.md`. Consult when a rule is challenged, or when a new model release may have moved a fact.

Gathered 2026-07-14.

## Sources

Anthropic (three guides, and they do not agree with each other):
- [Prompting Claude Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8)
- [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5)
- [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)

OpenAI:
- [GPT-5.6 Sol prompting guidance](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6) — the current model on this machine (`~/.codex/config.toml:1` is `gpt-5.6-sol`). Treat as primary.
- [Using GPT-5.6](https://developers.openai.com/api/docs/guides/latest-model)
- [Codex prompting](https://learn.chatgpt.com/docs/prompting)
- [Codex prompting guide (cookbook)](https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/gpt-5/codex_prompting_guide.ipynb) — older, Codex-Max era
- [AGENTS.md configuration](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## The one place the OpenAI docs contradict each other

This matters because the 早停 rule is built on it.

**Codex cookbook guide** says to remove *all* prompting for upfront plans, preambles, or status updates, because it "can cause the model to stop abruptly before the rollout is complete."

**GPT-5.6 Sol guidance §8** says the opposite about preambles: "Prompt for a short preamble before first tool call, then sparse updates at phase changes. Do not narrate routine calls."

Resolution used in `SKILL.md`, and it is an **inference, not a quote from either document**: the failure mode is a *plan delivered as an artifact* (a finishable turn), not a *preamble* (a sentence before working). The 5.6 guidance is newer and targets the model actually installed here, so it wins where they conflict. If Codex starts stopping early despite a preamble-only brief, this inference is wrong and the cookbook's broader ban should be restored.

## The table

| Issue | Anthropic | OpenAI (GPT-5.6 Sol) |
|---|---|---|
| Prompt detail | Opus 4.8 and Sonnet 5 read literally, do not generalize across items, do not infer unmade requests. State scope explicitly. **Fable 5 inverts this**: over-prescriptive prompts degrade its output. | Simplify first. Leaner system prompts scored 10-15% higher on internal evals, tokens down 41-66%, cost down 33-67%. |
| Absolute rules | Not flagged | Replace ALWAYS / NEVER with decision criteria for judgment calls |
| Repeating yourself | Not flagged | State each instruction once. Contradictions are worse than ignored: the model spends reasoning tokens reconciling them. |
| Step-by-step procedures | Fine; explicit scope is a virtue | Argued against. Describe the destination, let the model route. |
| Plan as a deliverable | Encouraged (`CLAUDE.md` rule 1 requires it) | Causes early stop. Use `/plan` as its own turn. |
| Preamble + phase updates | Encouraged | **Recommended** (§8). Routine call-by-call narration is not. |
| How to verify | Recommended | Mandatory. "Stop rules" and "Success criteria" are two of the eight canonical prompt sections. |
| Output length | Prompt for it; no parameter exists | `text.verbosity` parameter. Prefer it over prompting. |
| Intelligence dial | `effort`: low / medium / high / xhigh / max | `reasoning_effort`: none / low / medium / high / xhigh / max. **Raise it last**: first check whether the prompt is missing a success criterion, dependency rule, tool-routing rule, or verification loop. |
| Stating intent (the why) | Explicitly recommended | No equivalent guidance. Codex emphasizes repro steps and verification instead. |
| Canonical prompt structure | None given | Role / Personality / Goal / Success criteria / Constraints / Tools / Output / Stop rules. "Keep each section short. Add detail only where it changes behavior." |
| Migration discipline | Not flagged | "Do not rewrite a working prompt stack all at once." Switch model → keep effort → run evals → subtract → add only targeted fixes → re-run evals. |
| Project memory file | `CLAUDE.md`, no size limit | `AGENTS.md`, 32 KiB ceiling, injected as its own user message, merged global → repo root → nearest wins |

## Notes that expire

- Anthropic's three per-model guides disagree. Fable 5 in particular inverts the "be explicit and complete" advice. If Fable 5 becomes the default here, re-read `SKILL.md` against that guide before trusting the "add back scope" rule.
- OpenAI's Prompt Optimizer is scheduled for shutdown 2026-11-30. Do not build a workflow on it.
- The GPT-5.6 Sol guidance page gives no Markdown-vs-XML formatting guidance. Earlier 5.1 and 5.2 cookbook examples used XML-style tags for behavior blocks. Unresolved; do not assert a house format.
