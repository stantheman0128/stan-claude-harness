# Owned Prompt Template (Factor 2)

Treat the prompt as versioned source code, not a hidden framework string. Keep it in your repo, diff it in PRs, and test it.

## Structure

```
[ROLE / IDENTITY]
You are <role>. Your job is to <single clear objective>.

[OPERATING RULES]
- Always respond with exactly one tool call (structured JSON).
- Never invent data not present in the context.
- If you lack information a human must provide, call request_human_input.
- When the objective is complete, call done with a final_answer.

[AVAILABLE TOOLS]
<rendered from your tool schema — name, purpose, args. See tool-schema.md>

[OUTPUT CONTRACT]
Respond ONLY with a single JSON object matching one of the tool schemas. No prose.

[CONTEXT]
<rendered context — see context-format.md>
```

## Principles

- **One objective per prompt.** If the prompt has many jobs, you likely need multiple small agents (factor 10).
- **Make the output contract explicit and machine-checkable.** The LLM's only job is emitting a valid structured output (factors 1, 4).
- **No hidden state in the prompt.** Everything the model needs comes from the rendered context (factor 3), so runs are reproducible (factor 12).
- **Version it.** Store as a function/string constant, e.g. `PROMPT_V3`, and log which version produced each run.

## Anti-patterns

- Concatenating user input directly into instructions (prompt injection surface).
- Relying on a framework's default system prompt you've never read.
- Stuffing examples and rules that the model already follows — every token competes for context.
