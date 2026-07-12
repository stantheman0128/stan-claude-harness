# Technical SEO Checklist

Scoped to a small, single-author site (roughly under 500 pages, one language unless stated otherwise). Enterprise-only concerns (sitemap index files, large hreflang matrices, faceted-navigation canonicalization) are intentionally omitted.

## Meta title

No official character limit — the title link truncates to fit the device width in the SERP, so keep it descriptive and concise (~50-60 characters is a practical target). Every page needs a unique `<title>`. Avoid vague titles ("Home", "Profile"), avoid keyword stuffing, and make sure the visible on-page heading matches the title's intent since Google also pulls from prominent page text.

Source: [Google Search Central — Influencing Title Links](https://developers.google.com/search/docs/appearance/title-link)

## Meta description

No official length limit — Google truncates the snippet to fit device width (~150-160 characters practical target). Write a page-specific description for every important page (homepage, about, each project/case-study). Avoid duplicate/boilerplate descriptions across pages — Google will generate its own snippet from page content if yours isn't useful.

Source: [Google Search Central — How to Write Meta Descriptions](https://developers.google.com/search/docs/appearance/snippet)

## Open Graph

Four required properties per page (ogp.me): `og:title`, `og:type` (`website` or `profile` for a portfolio), `og:image`, `og:url` (set to the canonical URL). Recommended optional: `og:description`. If `og:image` is set, also set `og:image:alt` (a description, not a caption).

Source: [ogp.me — The Open Graph protocol](https://ogp.me/)

## Twitter/X Cards

Minimum: `twitter:card` — `summary_large_image` for image-heavy portfolio/project pages, `summary` otherwise. X's crawler falls back to the equivalent `og:*` values when `twitter:*` tags are missing, so a correct Open Graph block mostly covers this already. Keep `og:url`/`twitter:url` identical to the canonical URL — a mismatch can cause a stale cached preview.

Source: [X for Websites — Getting started with Cards](https://developer.x.com/en/docs/x-for-websites/cards/guides/getting-started)

## Structured data — Person

`schema.org/Person` as JSON-LD, minimum `name`, `url` (canonical homepage), `image`, `jobTitle`. Add `sameAs` as an array of URLs to the owner's own authoritative profiles (GitHub, LinkedIn, personal social accounts) — `sameAs` should only link pages that represent the exact same real-world identity, not merely related content.

Source: [schema.org/Person](https://schema.org/Person), [schema.org/sameAs](https://schema.org/sameAs)

## Structured data — WebSite

Add a `schema.org/WebSite` entity (`name` + `url`) on the homepage — gives search engines an unambiguous "site" entity distinct from the Person entity. Low effort, low risk.

Source: [schema.org/WebSite](https://schema.org/WebSite)

## Structured data — ProfilePage (usually not this)

Google's ProfilePage markup is specifically for pages where a creator posts first-hand content inside a larger community/forum context (it powers Google's Discussions-and-Forums feature) and requires a `mainEntity` (Person or Organization) with at least a `name` or `alternateName`. For a standalone personal portfolio (not a profile inside a larger platform), Person + WebSite JSON-LD on the homepage is the applicable pattern — only add ProfilePage if the page is genuinely a public profile/creator-page in Google's sense.

Source: [Google Search Central — Profile Page structured data](https://developers.google.com/search/docs/appearance/structured-data/profile-page), [schema.org/ProfilePage](https://schema.org/ProfilePage)

## Structured data — general rules

Prefer JSON-LD over Microdata/RDFa — Google's stated recommendation as the easiest format to implement/maintain at scale. Markup must describe content actually visible on that page; don't mark up content that isn't shown to users, and if one item in a visible list is marked up, all of them must be. The page carrying the markup must be crawlable (not blocked by robots.txt, `noindex`, or a login wall).

Source: [Google Search Central — General Structured Data Guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)

## Canonical tags

Add a self-referencing `rel="canonical"` to every page, even on a small single-version site, to lock in one preferred URL against http/https, www/non-www, and trailing-slash variants. Google ranks canonicalization signals by strength: **redirects (strongest) > `rel="canonical"` (weaker) > sitemap inclusion (weakest)** — use 301 redirects to force one host/protocol variant first, then reinforce with canonical. Keep internal links pointing at the canonical URL. Never send conflicting signals (one URL in the sitemap, a different canonical value on that page). Do not use robots.txt or a URL-removal tool for canonicalization.

Source: [Google Search Central — How to Specify a Canonical](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [What is URL Canonicalization](https://developers.google.com/search/docs/crawling-indexing/canonicalization)

## sitemap.xml protocol

UTF-8 encoded XML using the sitemaps.org namespace inside a `<urlset>` root. Each entry needs a `<url>` parent with a required `<loc>` child (`lastmod`/`changefreq`/`priority` are optional and inconsistently honored). All listed URLs must share the same host and protocol as the sitemap file's own location. Limits (50,000 URLs / 50MB, needing a sitemap index above that) are irrelevant at portfolio scale.

Google states a site under ~500 pages, fully reachable by following internal links from the homepage, generally doesn't *strictly* need a sitemap — but Google also recommends adding one anyway for new sites (few external links yet, the common case for a just-launched portfolio) or sites with meaningful rich media (project screenshots/video), since a sitemap helps crawlers discover content faster in the absence of many inbound links. Both statements come from the same source and aren't a contradiction to resolve — default to "add it," it's cheap.

Source: [sitemaps.org protocol](https://www.sitemaps.org/protocol.html), [Google Search Central — What Is a Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)

## robots.txt syntax

Exactly one file per site, plain text, must live at the root (`example.com/robots.txt`) — cannot be in a subdirectory. Default with no file (or no matching rule) is "allow all." Structure: a group starting with `User-agent:` (`*` for all crawlers), followed by `Allow:`/`Disallow:` path rules (path values are case-sensitive; major engines support `*` wildcards). Add a `Sitemap:` line pointing at the sitemap URL — ignored for rule-matching, but tells crawlers where to find it.

**Critical distinction**: robots.txt only blocks *crawling*, not *indexing* — a disallowed URL can still appear in search results if linked from elsewhere. To actually keep a page out of Google, use a `noindex` meta tag/header or password-protect it, not robots.txt.

Source: [Google Search Central — Robots.txt Introduction and Guide](https://developers.google.com/search/docs/crawling-indexing/robots/intro)

## hreflang — usually skip

Only relevant if the site genuinely publishes the same content in 2+ languages as separate URLs. If the site is single-language, skip hreflang entirely — it adds real maintenance risk since Google requires reciprocal/return links (every alternate URL must link back to every other alternate, including itself) or the annotations may be ignored outright. If used: `<link rel="alternate" hreflang="x">` tags in `<head>`, paired with a same-language canonical; only add `hreflang="x-default"` if there's a language-neutral landing/root page.

Source: [Google Search Central — Localized Versions of Your Pages](https://developers.google.com/search/docs/specialty/international/localized-versions)

## Core Web Vitals / page speed

Google names Core Web Vitals as signals its core ranking systems use: **LCP < 2.5s, INP < 200ms, CLS < 0.1**. There is no single "page experience score" that directly boosts rank — these are part of a broader signal set — but a good result is still worth pursuing. Portfolio sites are typically image/web-font-heavy: compress/lazy-load hero and project images, reserve layout space for images/fonts to avoid CLS, avoid render-blocking scripts to protect LCP/INP.

Source: [Google Search Central — Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals), [Understanding Google Page Experience](https://developers.google.com/search/docs/appearance/page-experience)

## Validating structured data

Two complementary official tools:
- **Google Rich Results Test** — checks whether JSON-LD is eligible for one of Google's ~30 supported rich-result search features and previews how it may look, but only validates Google-supported types.
- **Schema Markup Validator** (validator.schema.org) — the multi-vendor successor to Google's retired Structured Data Testing Tool (built with Microsoft/Yahoo/Yandex); checks correctness against the full schema.org vocabulary (800+ types) regardless of whether Google uses that type for a visible feature.

Workflow: validate with both, then spot-check via Search Console's URL Inspection tool after deploying. Passing validation does not guarantee a rich result will actually display.

Source: [Google Search Central — Structured Data Testing](https://developers.google.com/search/docs/appearance/structured-data)
