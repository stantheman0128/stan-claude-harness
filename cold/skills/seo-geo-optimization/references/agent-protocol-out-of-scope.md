# Agent-Protocol Surface — What's Actually Out of Scope

"AI agent readiness" auditors (isitagentready.com and similar) score a site against nine `.well-known`/DNS items. Nine failing items on such a report is not nine bugs — most of them only apply to sites that operate a live programmatic API, auth server, or MCP server for agents to call. This file gives the per-item reasoning so the judgment call isn't just "trust me."

## Skip entirely — require operating a live agent-facing service that doesn't exist on a marketing/portfolio site

| Item | What it asks you to publish | Why it doesn't apply |
|---|---|---|
| **DNS-AID** | DNSSEC-signed SVCB/HTTPS records under a `_agents.` subdomain (e.g. `_a2a._agents.example.com`) advertising the network endpoints of live agent protocols like A2A | Advertises agent-protocol endpoints the site doesn't run |
| **API Catalog** | `/.well-known/api-catalog` (RFC 9727, `application/linkset+json`) listing every API exposed, each linking to its OpenAPI spec, docs, and health endpoint | Lists specs for APIs that don't exist |
| **OAuth/OIDC discovery** | `/.well-known/openid-configuration` or `/.well-known/oauth-authorization-server` with `issuer`, `authorization_endpoint`, `token_endpoint`, `jwks_uri`, supported grant types | Requires actually running an OAuth/OIDC authorization server |
| **OAuth Protected Resource** | `/.well-known/oauth-protected-resource` (RFC 9728) naming which authorization server(s) issue tokens accepted by a protected resource | Requires a protected API resource and token-issuing auth servers |
| **auth.md** | `/auth.md` documenting how an agent registers for and obtains credentials to call the service | Documents a credential-registration flow for a service that requires no credentials |
| **MCP Server Card** | `/.well-known/mcp/server-card.json` (SEP-1649) with `serverInfo`, transport endpoint, and `capabilities` (tools/resources/prompts) | Describes tools/resources of an MCP server that isn't running |

**Why skipping these is correct, not lazy**: publishing metadata for an endpoint that doesn't exist either 404s (dead weight, no benefit) or — worse — creates a stale/misconfigured `.well-known` file that *looks* like a live service, which is a bigger red flag to an auditing agent than simply not having the file at all. Do not chase a 100/100 "agent readiness" score on a portfolio site by adding these six; that score is designed for API products.

## Conditional — only if the underlying thing genuinely exists

| Item | What it asks for | When it actually applies |
|---|---|---|
| **Agent Skills index** | `/.well-known/agent-skills/index.json` listing every SKILL.md/skill archive published, with name/type/description/url/sha256 | Only if the site is actually distributing invokable skill packages — a dev-tool/skill-marketplace use case, not a bio/portfolio |
| **WebMCP** | `navigator.modelContext.registerTool()` registering in-browser, agent-invocable actions with a JSON-Schema `inputSchema` and `execute` callback | Only if the page has real interactive client-side actions worth exposing (a booking widget, a meaningful search/filter with backend behavior) — a static portfolio's "actions" are just links, which agents can already follow; registering them as WebMCP tools adds surface area with no real benefit |

## The one item that's genuinely universal

**Markdown Negotiation** (`Accept: text/markdown` → markdown response) is the one item from this nine-part list that applies to a no-API portfolio site regardless. It's pure content accessibility, not an API/auth concern — see `geo-ai-discoverability.md` for the implementation pattern. It's covered in the main quick-reference table, not repeated here.
