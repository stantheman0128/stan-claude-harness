---
name: seo-geo-optimization
description: Use when improving a website's SEO (search-engine ranking) or GEO (AI answer-engine visibility — ChatGPT Search, Perplexity, Google AI Overviews, Claude web search) — triggers include "improve SEO", "why doesn't Google find my site", "GEO", "AI search visibility", "llms.txt", "robots.txt for AI crawlers", "AI readiness score", "make AI say good things about me", or a pasted Cloudflare / isitagentready.com audit report with failing checklist items. Also use before implementing meta tags, structured data, sitemap, or AI-crawler access changes on any site.
---

# SEO / GEO Optimization

## Overview

SEO gets a site ranked by classic search engines (Google, Bing). GEO (Generative Engine Optimization) gets a site cited/represented well by AI answer engines. Classic technical SEO is still the strongest lever for both — Google AI Overviews mostly re-ranks existing organic results. GEO-specific additions (llms.txt, Content Signals, AI-crawler allowlisting) are cheap, high-optionality add-ons layered on top, not a replacement.

**Scope**: marketing / portfolio / content sites — static or mostly-static, no user auth, no programmatic API exposed to agents. A site that offers real APIs/MCP servers/OAuth to agents needs a different playbook — see "What NOT to Implement" below for why that distinction matters.

## When to Use

- Improve SEO/GEO, or diagnose why a site isn't found on Google/AI search
- A pasted SEO/AI-readiness audit report (Cloudflare AI Readiness, isitagentready.com, Lighthouse) with failing items — decide what to actually fix
- Before implementing meta tags / structured data / sitemap / robots.txt changes

Not for: enterprise-scale sites (500+ pages, i18n at scale, faceted navigation) — those need dedicated technical-SEO expertise beyond this checklist. Not for sites that genuinely expose agent-callable APIs — different playbook, see below.

## Audit First, Always

Curl the live site and build a findings table (current state → pass/fail → fix) before changing anything.

```bash
curl -sI https://<domain>/                                     # status, redirects, cache headers
curl -s  https://<domain>/robots.txt                           # exists? Sitemap: line? Content-Signal?
curl -s  https://<domain>/sitemap.xml                          # valid XML? same host as the sitemap URL?
curl -s  https://<domain>/llms.txt                              # exists? H1 + summary?
curl -sI -H "Accept: text/markdown" https://<domain>/           # markdown negotiation already live?
curl -s  https://<domain>/ | grep -iE '<title>|meta name="description"|rel="canonical"|og:|twitter:|ld\+json'
```

Repeat the meta/OG/canonical/JSON-LD grep on 2-3 inner pages — duplicate-title bugs live there, not just the homepage. Run the same domain's robots.txt/homepage 3-5 times in a row: a domain that answers differently between requests (different title, random 401, different theme) usually means a stale DNS/parking-page/CDN-cache conflict, not a real content bug — chase that root cause before touching SEO tags. Validate structured data at validator.schema.org and Google's Rich Results Test once tags are in place.

## Quick Reference — Implement

| Area | Minimum | Detail |
|---|---|---|
| Meta title/description | unique per page, ~50-60 / ~150-160 char practical target | references/technical-seo-checklist.md |
| Canonical | self-referencing `rel=canonical` on every page; fix host/protocol variants with a 301 first (stronger signal), canonical reinforces | references/technical-seo-checklist.md |
| Open Graph | `og:title`, `og:type`, `og:image`, `og:url` (= canonical) | references/technical-seo-checklist.md |
| JSON-LD | Person (name/url/image/jobTitle/sameAs) + WebSite on the homepage; NOT ProfilePage unless the page is a profile inside a larger platform | references/technical-seo-checklist.md |
| sitemap.xml | UTF-8, sitemaps.org `<urlset>`, every `<loc>` shares host+protocol with the sitemap itself | references/technical-seo-checklist.md |
| robots.txt | one file, root only, has a `Sitemap:` line; blocks *crawling* not *indexing* — use `noindex` for real exclusion | references/technical-seo-checklist.md |
| Core Web Vitals | LCP < 2.5s, INP < 200ms, CLS < 0.1 | references/technical-seo-checklist.md |
| llms.txt | H1 = name/site, blockquote = one-line summary, H2 sections as link lists; not an official standard — Google ignores it, but agentic coding tools and some RAG pipelines read it | references/geo-ai-discoverability.md |
| Content Signals | `Content-Signal: search=yes, ai-input=?, ai-train=?` on robots.txt — ask the owner's actual preference for the last two, don't decide silently | references/geo-ai-discoverability.md |
| AI crawler allowlist | allow search/retrieval bots (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Amazonbot) if the goal is ever being cited — blocking them is zero citation chance, not neutral | references/geo-ai-discoverability.md |
| Markdown for agents | serve markdown on `Accept: text/markdown`; self-buildable from any content source, no paid feature required — see templates/seo-head.js pattern | references/geo-ai-discoverability.md |

## What NOT to Implement

An "AI agent readiness" audit (isitagentready.com and similar tools) checks for things that only apply to sites exposing a **live programmatic API, auth server, or MCP server to agents**: DNS-AID, API Catalog, OAuth discovery, OAuth Protected Resource, `/auth.md`, MCP Server Card. A marketing/portfolio site has none of those — these items *should* fail the audit, and that is correct, not a gap to close.

**Decision rule**: does the site operate a live agent-callable API, OAuth/OIDC authorization server, or MCP server *right now*? No → skip all six regardless of how official the checklist item looks.

**Red flag**: catching yourself about to build `/.well-known/oauth-authorization-server` (or similar) for a site with no auth server. Publishing metadata for an endpoint that doesn't exist either 404s (no benefit) or — worse — describes a service that looks live but isn't, which is a bigger red flag to an auditing agent than simply not having the file.

Two items are conditional, not blanket-skip: an agent-skills discovery index only matters if the site actually distributes invokable skill packages; WebMCP only matters if the page has real client-side actions worth exposing (a booking widget, a meaningful filter) — a portfolio's "actions" are just links agents can already follow. Full per-item reasoning: references/agent-protocol-out-of-scope.md.

## Common Mistakes

- **Treating llms.txt as a guaranteed citation lever.** It isn't — Google has said explicitly it doesn't use it as a signal. Do it because it costs almost nothing and some tools (agentic coding assistants, some RAG pipelines) do read it, not because it's proven to move rankings.
- **ProfilePage schema on a standalone portfolio.** ProfilePage is for a profile page *inside* a larger platform (it powers Google's Discussions-and-Forums feature). A standalone personal site wants Person + WebSite, not ProfilePage.
- **Incomplete JSON-LD.** A half-filled schema block can score *worse* than no schema at all (reported ~18-point citation penalty in one study). Fill a type out fully or skip it entirely.
- **On Cloudflare: assuming Managed robots.txt and Markdown-for-Agents agree.** They default to opposite Content-Signal values (`ai-train=no` vs `ai-train=yes`) with nothing reconciling them automatically — check both if both are enabled.
- **On Cloudflare: a fixed Edge TTL override serving stale HTML after a redeploy** — to crawlers as much as browsers, including references to deleted post-redeploy JS/CSS bundle hashes. Use `respect_origin` + proper origin `Cache-Control`, not a dashboard TTL override.
- **Lumping all "AI bots" together.** Training crawlers (GPTBot, ClaudeBot, Google-Extended), search/retrieval crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot), and user-triggered fetchers (ChatGPT-User, Claude-User) serve different purposes — a blanket Disallow or blanket Allow throws away a real decision the owner should get to make.
- **Assuming apex, www, and the host's preview subdomain behave identically.** AI Crawl Control, Content Signals, and canonical all key off ONE domain — verify production traffic actually flows through it, and that a stale registrar parking page or preview subdomain isn't silently shadowing it.

## References

- `references/technical-seo-checklist.md` — full technical SEO detail (meta, OG, Twitter cards, JSON-LD, sitemap, robots.txt, hreflang, Core Web Vitals, validation tools)
- `references/geo-ai-discoverability.md` — full GEO detail (llms.txt spec, Content Signals, AI crawler tiers, markdown-for-agents pattern, entity/E-E-A-T, content-citation drivers, measurement)
- `references/agent-protocol-out-of-scope.md` — the isitagentready.com 9-item breakdown, what to skip and why
- `references/cloudflare-notes.md` — Cloudflare-specific: AI Crawl Control layering, Managed robots.txt, Markdown for Agents plan-gating, Cache Rules gotcha
- `templates/seo-head.js` — worked JS pattern for canonical + OG + JSON-LD generation, adapted from a real shipped implementation
- `templates/robots.txt.example`, `templates/llms.txt.example` — starting points to adapt

## Prior Art

Community Claude Code SEO skills worth a look if this checklist needs extending (summarized via research, not independently verified line-by-line — treat as leads, not endorsements): `aevans-eng/seo-skill` (closest scope match — static portfolio-specific), `AgriciDaniel/claude-seo` (large agency-grade pack; argues GEO is "largely rebranded SEO," a useful counterweight to GEO hype), `TheSmokeDev/geo-skills` (weighted scoring rubric across AI Citability / Brand Authority / E-E-A-T / Technical GEO / Schema / Platform).
