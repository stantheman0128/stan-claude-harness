# Candidate categories

**A menu, not a checklist.** Read it to notice what you might be missing. Do not instantiate a category because it appears here. A category with nothing real behind it produces sediment, and sediment reads exactly like knowledge.

Merge freely. Split where a project is deep. Add categories nobody thought of. If the repo honestly yields five skills, ship five.

Adapted from a widely-shared "retiring principal" prompt (2026-07). The original prescribed 10 to 16 skills across a fixed 16-category taxonomy. The count anchor is removed here on purpose: a prescribed taxonomy applied to a real repo manufactures content for its thin categories, and the original's own "no oversell" rule fights its own taxonomy.

## Usually real

- **change-control** — how changes are classified, gated, reviewed here; the non-negotiables, each with the incident that created it.
- **debugging-playbook** — symptom to triage table for this project's failure modes; the traps that cost real time, each with its story; the experiment that discriminates between two candidate causes.
- **failure-archaeology** — the chronicle of settled battles: symptom, root cause, evidence, status. Highest hallucination risk in the set; every entry needs a commit, PR, or issue that *states the reason*, or it gets deleted. See the archaeology exception in `SKILL.md`.
- **architecture-contract** — the load-bearing design decisions and why; the invariants that must hold; the known-weak points, stated plainly.
- **build-and-env** — recreate the environment from scratch; the traps.
- **run-and-operate** — running or deploying it: command anatomy, artifact conventions, what output lands where.
- **validation-and-qa** — what counts as evidence here; the acceptance bar; the golden inventory; how to add a test.

## Real in some projects

- **domain-reference** — the domain theory a mid-level person lacks, as it applies *here*. Not a textbook chapter.
- **config-and-flags** — every configuration axis: options, defaults, production versus experimental, guards; how to add one. Flags drift, so this one needs re-verification commands more than any other.
- **diagnostics-and-tooling** — how to measure instead of eyeball. Ship the actual scripts in the skill's `scripts/` directory.
- **docs-and-writing** — maintaining the docs of record; templates; house style. Usually user-invoked.
- **external-positioning** — papers, releases, ecosystem: what is novel versus known, what must be proven before claiming it. Usually user-invoked, and usually absent.

## Speculative — justify before writing

The original prompt's "ADVANCED" tier. These are where a template most reliably generates impressive-sounding fluff. A Chrome extension that tracks board games does not have a research frontier. Write one of these only if Phase 1 surfaced something concrete that demands it.

- **`<hardest-problem>`-campaign** — an executable, decision-gated campaign for the hardest live problem: numbered phases, exact commands, the *expected* observation at every gate ("if you see X instead, branch to Y"), the ranked solution menu, the wrong paths explicitly fenced off, and a promotion protocol routed through the project's own change control. This one is genuinely valuable when there *is* a hard live problem. It is the best idea in the original prompt.
- **proof-and-analysis-toolkit** — the first-principles methods of the domain, each as a recipe with a worked example from this repo's history.
- **research-frontier** — open problems where this project could advance the state of the art. For each: why current approaches fail, this project's specific asset, the first three concrete steps *in this repo*, and a falsifiable "you have a result when…" milestone. Almost always fluff. Justify hard.
- **research-methodology** — the discipline that turns a hunch into an accepted result here: the evidence bar, hypothesis-predicts-numbers-before-running, the idea lifecycle from experiment flag to adopted change or documented retirement.
