# Vendor differences: Anthropic vs OpenAI

Sourced backing for the rules in `SKILL.md`. Consult when a rule is challenged or when a new model release might have moved a fact.

Gathered 2026-07-14.

## Sources

Anthropic:
- [Prompting Claude Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8)
- [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5)
- [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)

OpenAI:
- [Using GPT-5.6](https://developers.openai.com/api/docs/guides/latest-model)
- [Codex prompting](https://learn.chatgpt.com/docs/prompting)
- [Codex prompting guide (cookbook)](https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/gpt-5/codex_prompting_guide.ipynb)
- [GPT-5.2 prompting guide](https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/gpt-5/gpt-5-2_prompting_guide.ipynb)
- [AGENTS.md configuration](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## The table

| Issue | Anthropic | OpenAI |
|---|---|---|
| Prompt detail | Opus 4.8 and Sonnet 5 read literally, do not generalize across items, do not infer unmade requests. State scope explicitly. | Leaner system prompts scored 10-15% higher on internal coding evals while cutting tokens 41-66% and cost 33-67%. |
| Repeating yourself | Not flagged | "State each instruction once." Contradictions are worse than ignored: GPT-5 spends reasoning tokens trying to reconcile them. |
| Step-by-step procedures | Fine, and explicit scope is a virtue | Codex docs argue against them. Describe the outcome, let the model choose the approach. |
| Upfront plan / preamble / progress updates | Encouraged. Opus 4.8 is praised for higher-quality progress updates. | **Remove them.** Verbatim from the Codex guide: prompting for an upfront plan, preambles, or status updates "can cause the model to stop abruptly before the rollout is complete." |
| How to verify | Recommended | Mandatory. One of the four elements of the official Codex brief formula. |
| Output length | Prompt for it | `text.verbosity` API parameter. Docs say prefer the parameter over the prompt. |
| Intelligence dial | `effort`: low / medium / high / xhigh / max | `reasoning_effort`: none / low / medium / high / xhigh / max. The extra `none` forces zero reasoning tokens. |
| Stating intent (the why) | Explicitly recommended, especially for long-running agents | No equivalent guidance. Codex emphasizes repro steps and verification instead. |
| Over-prescription | Only Fable 5 degrades from it; Opus 4.8 and Sonnet 5 want the detail | Warned against across the whole 5.x line |
| Project memory file | `CLAUDE.md`, no size limit | `AGENTS.md`, 32 KiB ceiling (`project_doc_max_bytes`), injected as its own user message, merged global → repo root → nearest directory wins |

## Notes that expire

- Anthropic's per-model guides split three ways today (Opus 4.8 / Sonnet 5 / Fable 5) and the three do not agree with each other. Fable 5 in particular inverts the "be explicit and complete" advice: over-prescriptive skills written for earlier models degrade its output. If Fable 5 becomes the default model here, re-read `SKILL.md` against that guide before trusting the "add back scope" rule.
- OpenAI's Prompt Optimizer is scheduled for shutdown on 2026-11-30. Do not build a workflow on it.
- No dedicated GPT-5.6 cookbook prompting guide exists yet; the 5.6 guidance lives in the `latest-model` API doc.
