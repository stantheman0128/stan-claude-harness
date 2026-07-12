# GEO / AI Discoverability

## llms.txt

Spec at [llmstxt.org](https://llmstxt.org/) (Jeremy Howard / Answer.AI): a Markdown file at site root (`/llms.txt`). Only the H1 title is required. Recommended structure, in order:

1. `# Site or person name` (H1)
2. `> one-paragraph summary` (blockquote — key facts, concise)
3. optional free-form Markdown detail paragraphs
4. zero or more `## Section` headings listing links as `- [Title](url): description`
5. an optional final `## Optional` section for lower-priority links that can be dropped under tight context windows

Companion conventions: `llms-full.txt` (single concatenated full-text version of the whole site) and per-page `.md` variants (append `.md` to a URL) so agents can fetch clean Markdown instead of parsing HTML.

**Honest framing**: llms.txt is *not* an official web standard (no IETF/W3C backing) and adoption by the big AI search products is thin. Google has explicitly said it does not use llms.txt as a signal (a Google engineer compared it to the old meta-keywords tag), and John Mueller has said Google has no plans to honor it. It *is* actively read by IDE/agentic coding tools (Cursor, Windsurf, Claude Code, GitHub Copilot) and by some RAG/agent pipelines. Treat it as low-cost, high-optionality — not a guaranteed citation lever. The community itself disagrees: some SEO skill packages generate/validate it, others explicitly label "llms.txt is a citation lever" a myth. Given the cost is near zero, doing it anyway is defensible; presenting it as proven best practice is not.

For a personal site, a Q&A-style structure works well: H1 = name, blockquote = one-line professional summary, then sections like Background / Projects / Skills / Contact, optionally phrased as questions ("Who is X", "What has X built", "How to contact X").

## Content Signals (robots.txt extension)

Spec at [contentsignals.org](https://contentsignals.org/) (launched by Cloudflare, CC0-licensed, framed as an EU DSM Directive Article 4 rights-reservation mechanism). Three categories, expressed as a comma-delimited yes/no list on a `Content-Signal` line paired with a `User-agent` block:

```
User-Agent: *
Content-Signal: search=yes, ai-input=yes, ai-train=no
Allow: /
```

- `search` — build a search index, show excerpts + links (classic search behavior)
- `ai-input` — feed content into AI for real-time answers (RAG/grounding)
- `ai-train` — train/fine-tune models on the content

Omitting a signal means neither granted nor restricted. Cloudflare added a 4th optional field, `content-use`, describing what a crawler may retain/reuse after accessing content (roughly: verbatim reproduction vs. aggregate/summarized use vs. reference/citation-only), e.g. `Content-Signal: search=yes,ai-train=no,use=reference`.

**These are preferences, not enforcement** — crawlers can ignore them, and Google has publicly stated it does not currently honor the directive at all. Still worth setting explicitly (costs nothing) rather than leaving a neutral/no-preference default, since some vendors do read it.

Default recommendation for a personal portfolio with no paywalled/proprietary content: `search=yes` always; `ai-train`/`ai-input` are genuine personal-preference calls — present the choice to the owner, don't decide silently.

## AI crawler tiers

Don't lump "AI bots" into one bucket — they serve different purposes:

1. **Training crawlers** (fetch to build/improve model training corpora): GPTBot (OpenAI), ClaudeBot (Anthropic), Google-Extended (Google Gemini/Vertex training opt-out token), Applebot-Extended (Apple Intelligence), CCBot (Common Crawl, feeds many third-party model trainers), Bytespider (ByteDance/TikTok — claims robots.txt compliance but has been observed ignoring `Disallow` on some sites; treat with suspicion).
2. **Search/retrieval crawlers** (fetch to build a live index used to ground AI answers, distinct from training): OAI-SearchBot (ChatGPT search), Claude-SearchBot (Anthropic — powers Claude's web search tool), PerplexityBot, Amazonbot (Alexa/Amazon AI answers). **Allow these** if the goal is ever being cited in an AI answer — blocking them is zero chance of citation, not a neutral choice.
3. **User-triggered fetchers** (fire only when an end user asks the assistant to look at a specific page, not for indexing): ChatGPT-User, Claude-User, Google-Agent/NotebookLM. Google's user-proxy fetchers explicitly ignore robots.txt because Google treats them as acting on behalf of a human.

Anthropic's three bots are functionally separate and each independently respects robots.txt (including `Crawl-delay`): **ClaudeBot** = training-data collection; **Claude-User** = fetches a specific page only when a Claude user asks about it (blocking it may reduce visibility for user-directed web search); **Claude-SearchBot** = crawls to power Claude's built-in web-search/answer feature (blocking it may reduce visibility/accuracy there). Blocking one does not block the others — address all three separately. Anthropic does not publish IP ranges (unlike OpenAI/Google/Perplexity/Bing); reverse-DNS is the fallback verification method.

Recommended 2026 pattern: explicitly **allow** the search/retrieval bots (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Amazonbot). Make a deliberate per-vendor call on the training bots — for a public portfolio with no proprietary data, allowing them costs nothing and training inclusion is itself a slow, indirect path to being "known" by a model; blocking them is a legitimate choice mainly for sites with paywalled/licensable content.

## Markdown-for-agents content negotiation

Pattern: when a request sends `Accept: text/markdown`, serve a clean Markdown rendition instead of full HTML/CSS, with `Content-Type: text/markdown`, `vary: accept`, and ideally an `x-markdown-tokens` estimate header.

**This is self-buildable and free** on any stack that controls its own response headers — it does not require a paid platform feature. Pattern: render the page content to Markdown from the same data source as the HTML (so it can never drift), branch on the `Accept` header in the route/function handler, return the Markdown payload with the right content-type when requested. See `templates/seo-head.js` for a worked JS example of the surrounding head-tag generation this pairs with.

Cloudflare has a first-party equivalent ("Markdown for Agents") gated to Pro+ plans — see `cloudflare-notes.md` if the site is Cloudflare-hosted and on a paid plan, since it comes with its own gotchas.

## Entity / off-site corroboration (E-E-A-T for a person)

AI answer engines use multi-source corroboration — they trust a fact/entity more when it's stated consistently across multiple independent domains, not just the owner's own site.

- Keep the name/brand string byte-for-byte consistent across the owner's site, GitHub, LinkedIn, and any press/bio mentions, so systems resolve one canonical entity instead of several ambiguous ones.
- `sameAs` in Person JSON-LD should only link true same-identity profiles.
- Reported highest-value off-site domains for individual citation as of early-2026 data: GitHub, LinkedIn, Reddit.
- A Wikidata entry (QID) — even without a full Wikipedia article — gives models an unambiguous, structured anchor point to resolve identity against. Low-effort, high-leverage, but a stretch item, not core scope.

## Content-quality levers for AI citation

Findings attributed to a widely-cited empirical GEO study (~10,000 queries), presented here as best-current-evidence, not proven causality — no research pass here read the underlying methodology directly:

- Cited statistics/data: **+30%** citation likelihood
- Quotations with clear attribution: **+40%+** (models treat quotation + attribution as a credibility proxy)
- Inline citations to reputable sources: **+30%**
- Keyword-stuffing: **-9%** (measurably hurts — degrades natural text flow, detectable via perplexity)

Structural tactics that show up consistently across current GEO guides:
- A direct, self-contained ~40-70 word answer to the core question in the *first paragraph* (retrieval systems weight opening content heavily, often only pulling the top chunk)
- Real semantic headings (H1/H2/H3) mirroring likely user questions, so pages chunk cleanly
- Genuine FAQ-style Q&A blocks
- Tables/lists for comparable facts (numbers, dates, specs) — structured data is easier to lift verbatim
- A visible "last updated" date; stale pages reportedly lose AI citations at a markedly higher rate than actively maintained ones

## Measurement

No Search-Console-equivalent exists yet for AI answer engines. Practical KPIs, tracked via periodic manual/scripted spot-checks of the target name/brand + query set across ChatGPT search, Perplexity, Google AI Overviews, and Claude web search:

- **Mention Rate** — % of AI answers to target queries that mention the site/person at all
- **Citation Rate** — % that include an actual clickable link (a stricter bar than mention)
- **Position/prominence** within the answer

This is an ongoing manual process, not a one-time implementation task — flag it as such rather than treating it as "done" after shipping the technical checklist.

## The counter-view worth stating out loud

Not every practitioner agrees GEO is a distinct discipline: one widely-used community skill argues GEO/AEO is largely rebranded classic SEO, since AI Overviews reportedly use the same underlying ranking/indexing signals as organic search — and explicitly flags "llms.txt is a citation lever," "content chunking is required for AI," and "AI-specific keyword rewriting is necessary" as myths. This is a real, unresolved debate, not settled practice. It's a reasonable counterweight against over-building the GEO layer of this checklist — do the cheap items because they're cheap, not because their ROI is proven.
