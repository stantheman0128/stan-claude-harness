---
name: 12-factor-review
description: Review or audit an existing AI agent codebase against the 12-factor agents methodology. Use when the user asks to review agent code, audit an agentic app, check why an agent is unreliable, or asks "is my agent well-built". Runs a deterministic scanner (scripts/audit.ts) for factor violations (hidden framework prompts, unbounded loops, no retry caps, mega-agents, scattered state, missing human-in-loop) then guides a structured manual review.
---

# 12-Factor Review

> Based on [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) by Dexter Horthy, adapted by tika/12-factor-agent-skills. Licensed CC BY-SA 4.0.

Audit an existing agent against the 12 factors. Combine the **deterministic scanner** (fast, repeatable signals) with a **manual review** (judgment). Factor definitions: [../12-factor-agents/references/factors.md](../12-factor-agents/references/factors.md).

## Step 1: Run the scanner

The scanner produces heuristic signals — starting points, not verdicts. Run it on the agent's source directory:

```bash
npx tsx scripts/audit.ts <path-to-agent-src>
# or, on Node 23.6+: node scripts/audit.ts <path-to-agent-src>
# JSON output for tooling:
npx tsx scripts/audit.ts <path-to-agent-src> --json
```

It prints a factor-by-factor report (`PASS` / `WARN` / `INFO`) with the files that triggered each signal. Read the WARNs first.

## Step 2: Confirm signals by reading code

For each WARN, open the cited files and confirm whether it's a real violation. The scanner uses text heuristics; a hit is a question to answer, not a guilty verdict.

## Step 3: Manual review checklist

Work top to bottom. Cite the factor in every finding.

- **Prompts hidden in a framework / never read?** → factor 2. Extract and own them.
- **Context = raw message array with no curation/compaction?** → factor 3. Curate what the LLM sees.
- **Outputs not validated against a schema?** → factor 4. Parse + validate at the boundary.
- **Two parallel state stores (execution vs business)?** → factor 5. Unify.
- **Can't pause and resume mid-run from saved state?** → factors 6, 12.
- **Human approval done as an out-of-band hack?** → factor 7. Make it a tool call.
- **Control flow fully delegated to a framework's until-done loop?** → factor 8. Take ownership.
- **No retry cap / errors not summarized back into context?** → factor 9. Compact + cap + escalate.
- **One giant agent doing 20+ steps?** → factor 10. Decompose.
- **Agent only launches from one UI?** → factor 11. Decouple trigger from execution.
- **State not serializable / hidden in closures or globals?** → factor 12. Make it a pure reducer.

## Step 3.5: Evidence gate before scoring

Do not rate any factor Strong / Partial / Weak until you have concrete evidence for it. Before writing a verdict, each factor needs at least one citation with a **file path plus a line range or a short quoted snippet** from the codebase, or an explicit "no evidence located after targeted reads" note. If evidence is still missing after searching, default that factor to Weak unless the criterion is clearly N/A (say why). Recommendations may name new files or patterns only as proposals, never as observed facts without a matching citation. （證據閘 harvest 自 existential-birds/beagle, Apache 2.0）

## Step 4: Report

Use this format:

```markdown
## Agent review: <name>

### Scanner summary
<counts of PASS/WARN per factor>

### Blocking issues
- [Factor N] <issue> — <file:line> — <fix>

### Suggestions
1. [Factor N] <improvement> — <where/why/how>

### Strengths
- <what the agent already does well>
```

Prioritize factors 2, 3, 8, 9, 10 — they cause the most real-world unreliability.
