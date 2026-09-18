# Cloudflare-Specific Notes

Only relevant if the site is hosted on Cloudflare Pages/Workers/a Cloudflare-proxied zone.

## Three layers, stacked, not the same thing

1. **Bot Management / Bot Fight Mode** — network-level bot detection/blocking, evaluated earliest. Can block AI Crawl Control's own actions if misconfigured (e.g. "Block AI Bots" intercepts a request before Pay Per Crawl can charge/allow it — must be turned off for Pay Per Crawl to work).
2. **AI Crawl Control** — per-AI-crawler allow/block/charge, technically enforced via an auto-generated WAF custom rule (or Pay Per Crawl).
3. **robots.txt + Content Signals** — a text file of directives that compliant crawlers voluntarily read. Cloudflare's own docs state plainly: "robots.txt compliance is voluntary... it does not prevent crawlers from accessing your content at a technical level." Cloudflare recommends pairing robots.txt (preference) with AI Crawl Control (enforcement), not relying on either alone.

## Managed robots.txt

Toggle under Security Settings → Bot traffic (also a Quick Action inside AI Crawl Control). If the origin already serves a robots.txt (HTTP 200), Cloudflare *prepends* its managed AI-crawler `Disallow` rules before the existing ones; if there's none, it generates one from scratch. **Default Content Signal when enabled: `search=yes, ai-train=no`** — verify this matches the actual preference, don't assume. A "Display Content Signals Policy" boilerplate text block can be toggled off separately if unwanted in the file.

On the Free plan, with no custom robots.txt and managed robots.txt disabled, Cloudflare auto-serves a neutral Content Signals Policy defining the categories but expressing **no preference** — turning on managed robots.txt is required to actually set values.

## Markdown for Agents — plan-gated, and inconsistent with the above

Gated to **Pro, Business, Enterprise, or SSL-for-SaaS plans** (not Free), included at no extra cost within those plans. Content-negotiation feature: `Accept: text/markdown` → Cloudflare fetches the origin HTML and converts to Markdown at the edge in real time. Output: optional YAML frontmatter (title/description/image from meta tags) + converted body with nav/header/footer stripped + an optional trailing fenced code block preserving any JSON-LD from the page, plus `x-markdown-tokens`/`x-original-tokens` headers and a `vary: accept` header. Limits: HTML-only, origin response capped at 2MB.

**Known gotcha**: Markdown for Agents stamps its own Content-Signal response header defaulting to `ai-train=yes, search=yes, ai-input=yes` — the **opposite** of Managed robots.txt's `ai-train=no` default. These are two independent mechanisms with independent, currently inconsistent defaults; enabling Markdown for Agents does not inherit the robots.txt AI-training preference, and there's no UI to reconcile them as of the last docs check. **Check both settings explicitly if both are enabled** rather than assuming they compose.

A self-built version (see `templates/seo-head.js` and the main SKILL.md quick reference) avoids this inconsistency entirely, since the same code path controls both the HTML and the Markdown response.

## AI Crawl Control dashboard

Tabs: Overview, Metrics, Crawlers, Robots.txt, Settings. Available on every plan for visibility; detection quality is plan-gated (Free = User-Agent string only, spoofable; paid = Cloudflare's Bot Management detection ID). The Robots.txt tab (added Oct 2025) monitors file health, tracks request volume/success, checks whether Content Signals directives are present, and flags crawlers requesting `Disallow`'d paths — actionable non-compliance signal.

## Cache Rules / Edge TTL — a real failure mode, not theoretical

Cache behavior is crawler-agnostic (doesn't distinguish AI bots from browsers) but affects what any crawler/agent sees. Edge TTL modes:
- `respect_origin` — use origin `Cache-Control` if present, else Cloudflare default
- `override_origin` — ignore `Cache-Control` entirely, apply a fixed TTL
- `bypass_by_default` — use `Cache-Control` if present, else skip caching

Header precedence: `cloudflare-cdn-cache-control` (Cloudflare-only, stripped before reaching the client) > `cdn-cache-control` (passed to downstream CDNs) > standard `Cache-Control` (passed to browsers/crawlers).

**A fixed override TTL can serve stale HTML — including references to deleted post-redeploy JS/CSS bundle hashes — to both browsers and any AI crawler/agent until the cache is manually purged.** Use `respect_origin` plus proper origin-set `Cache-Control` (`no-store` for pages that must never be stale, not `max-age=0`, which Cloudflare treats as "cache and revalidate" when Origin Cache Control is on). This is the same failure class regardless of whether the request is a human or a crawler — check it as basic operational hygiene whenever auditing a Cloudflare-hosted site's SEO/GEO surface.

## Domain scope

AI Crawl Control, Managed robots.txt, and Content Signals are all **zone-scoped to the custom domain** — they do not extend to `*.pages.dev`/`*.workers.dev` preview subdomains or branch-preview alias URLs. Verify production traffic actually flows through the custom domain, and that preview/parking-page domains aren't publicly linked or are Access-gated (Cloudflare provides no automatic `noindex` handling for these).

## Don't confuse with Cloudflare AI Search

Cloudflare **AI Search** (`developers.cloudflare.com/ai-search/`) is a *different* product — Cloudflare's own managed RAG/search service for building search into an app/agent (index a website, R2 bucket, or uploaded docs; query via Workers binding, REST API, or MCP endpoint). It is not a tool for controlling how external AI crawlers see a site. Its own crawler only touches domains explicitly added as a data source within the same Cloudflare account. Its website crawler does rely on the same sitemap.xml already recommended for classic SEO (priority: dashboard-set sitemap URL → sitemap(s) listed in robots.txt → `/sitemap.xml` → uncrawlable), so a clean sitemap benefits this product too even though it's a separate concern from AI Crawl Control.
