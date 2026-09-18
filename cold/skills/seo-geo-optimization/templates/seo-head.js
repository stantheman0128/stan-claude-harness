// Worked pattern for canonical + OG/Twitter + Person/WebSite JSON-LD + a
// self-built "Markdown for Agents" content negotiation, adapted from a real
// shipped implementation. Not a library — copy and adjust field names to the
// target site's own content model. Framework-agnostic (plain string templates);
// port to JSX/template-literals/whatever the target stack uses.

const ORIGIN = "https://example.com"; // TODO: real domain
const OG_IMAGE = ORIGIN + "/assets/social-preview.png"; // TODO: real 1200x630(ish) image
const SITE_NAME = "Example Person — Personal Website"; // TODO

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// One function, reused by every page/theme that exists — this is the whole
// point: canonical/OG/JSON-LD can never drift from what a given theme renders
// because everything reads from the same `profile` object.
export function seoHead(profile, { path = "/", title, desc } = {}) {
  const canonical = ORIGIN + path;
  const t = title || [profile.name, profile.role].filter(Boolean).join(" — ");
  const d = desc || profile.description || "";

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Person",
        "@id": ORIGIN + "/#person",
        name: profile.name,
        // Add every name/handle real people actually search for — this is
        // what lets "Full Legal Name", "Nickname", and "handle10" all
        // resolve to the same entity for an AI answer engine.
        alternateName: profile.alternateNames || [],
        url: ORIGIN + "/",
        image: OG_IMAGE,
        jobTitle: profile.role || undefined,
        description: d,
        // Only true same-identity profiles belong here — not merely
        // related/topical links.
        sameAs: (profile.sameAs || []).filter(Boolean),
      },
      {
        "@type": "WebSite",
        "@id": ORIGIN + "/#website",
        url: ORIGIN + "/",
        name: SITE_NAME,
        about: { "@id": ORIGIN + "/#person" },
      },
    ],
  };

  return [
    `<link rel="canonical" href="${canonical}">`,
    `<meta property="og:type" content="website">`,
    `<meta property="og:site_name" content="${esc(SITE_NAME)}">`,
    `<meta property="og:title" content="${esc(t)}">`,
    `<meta property="og:description" content="${esc(d)}">`,
    `<meta property="og:url" content="${canonical}">`,
    `<meta property="og:image" content="${OG_IMAGE}">`,
    `<meta name="twitter:card" content="summary">`,
    `<meta name="twitter:title" content="${esc(t)}">`,
    `<meta name="twitter:description" content="${esc(d)}">`,
    // < guard: makes "</script>" impossible inside the JSON payload.
    `<script type="application/ld+json">${JSON.stringify(jsonLd).replace(/</g, "\\u003c")}</script>`,
  ].join("\n");
}

// Self-built "Markdown for Agents" — no paid platform feature required.
// Render markdown from the SAME content source as the HTML, then branch on
// Accept in whatever serves the page (edge function, server route, etc.).
export function renderMarkdown(content) {
  const p = content.profile || {};
  const lines = [
    `# ${p.name}`,
    "",
    p.role ? `**${p.role}**` : "",
    p.description || "",
    "",
  ];
  for (const item of content.items || []) {
    lines.push(`## ${item.title}`, item.description || "", "");
  }
  return lines.filter((l) => l !== "").join("\n");
}

// Example route/function handler — adapt to the real framework.
//
// export function onRequest(context) {
//   const accept = context.request.headers.get("accept") || "";
//   if (accept.includes("text/markdown")) {
//     return new Response(renderMarkdown(content), {
//       headers: {
//         "content-type": "text/markdown; charset=utf-8",
//         "x-markdown-tokens": String(Math.ceil(md.length / 4)),
//         vary: "accept",
//       },
//     });
//   }
//   return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", vary: "accept" } });
// }
