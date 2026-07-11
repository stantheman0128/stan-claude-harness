# impeccable — Stan overlay patch 檔（重貼指引）

plugin 升級會建新版本目錄、不會帶走這些 overlay。**每次 `claude plugin update impeccable` 後，把本檔各段重貼進新版本目錄的對應檔案**（路徑：`~/.claude/plugins/cache/impeccable/impeccable/<新版本>/skills/impeccable/`）。貼完用 `grep -rn "Stan overlay" <新版本目錄>` 驗證 4 個標記都在。

目前套用於：3.9.1（2026-07-11 升級；共 5 個標記行、10 條規則，grep 實測 5）。升級法備註：3.8.0→3.9.1 上游沒動 animate.md/harden.md，用「copy-forward 舊檔」代替手動重貼、零轉錄風險——之後升級若上游同樣沒動 overlay 所在檔，優先用這招。3.9.1 仍無 ios.md/android.md。
相關記憶：[[project-impeccable-overlay]]。升級注意：上游 3.9.x 的 critique/layout/typeset 已改雙隔離 subagent、HEAD 有未釋出的原生平台層（ios.md/android.md——出了之後 LINE Notify+ 的 PRODUCT.md 要加 `## Platform: android`）。可考慮把 taste 兩條 bans 開 PR 回饋上游（Apache-2.0 相容），成功就少貼半套。

---

## 1. `SKILL.md` — Absolute bans 清單尾端（2026-07-05，源 Leonxlnx/taste-skill，MIT）

```markdown
<!-- Stan overlay 2026-07-05: next 2 bans harvested from Leonxlnx/taste-skill (MIT). Re-apply if a plugin update overwrites this file. -->
- **The Jane Doe effect.** Generic placeholder people (Jane Doe, John Smith, stock-smile avatars) and too-perfect metrics (99.99% uptime, 50% faster, 10x growth) in demo copy. Invent specific, plausible names and jagged numbers (98.7%, 43%), or use real content.
- **The premium-consumer palette rotation.** Beige + brass/gold + oxblood + espresso deployed as a set because the brief says "premium" or "luxury". Every AI-generated luxury site ships this exact skin. Any one of these colors can be right alone; the four-piece uniform is the tell.
```

## 2. `reference/animate.md` — Accessibility 節的 NEVER 清單（2026-07-05＋2026-07-10，源 emilkowalski/skills，MIT）

插在「Enter from `scale(0)`…」與「Use bounce or elastic…」之間：

```markdown
<!-- Stan overlay 2026-07-05: next 2 rules harvested from emilkowalski/skills (MIT). Re-apply if a plugin update overwrites this file. -->
- Animate keyboard-initiated or high-frequency actions (100+ times a day: shortcuts, command palettes, tab switches); repetition makes motion feel slow, not smooth
- Enter from `scale(0)`; nothing in the physical world appears from nothing. Use `scale(0.95)` + `opacity: 0` instead
<!-- Stan overlay 2026-07-10: next 2 rules harvested from emilkowalski/skills (MIT). Re-apply if a plugin update overwrites this file. -->
- Scale popovers/dropdowns/tooltips from the default center origin; set `transform-origin` to the trigger side so they grow from where they came from (Radix exposes `--radix-*-content-transform-origin`). Modals are exempt — they own the screen
- Animate Framer Motion `x`/`y` shorthands for performance-critical motion; independent transforms skip hardware acceleration — animate the full `transform` string instead
```

## 3. `reference/animate.md` — Accessibility 節的 reduced-motion CSS 區塊之後（2026-07-10，源 emilkowalski/skills，MIT）

```markdown
<!-- Stan overlay 2026-07-10: harvested from emilkowalski/skills (MIT). Motion Materials above promotes glass/backdrop-filter surfaces — these two fallbacks cover the a11y signals those surfaces need. Re-apply if a plugin update overwrites this file. -->
```css
@media (prefers-reduced-transparency: reduce) {
  .glass { backdrop-filter: none; background: var(--surface-solid); }
}
@media (prefers-contrast: more) {
  .glass, .card { border: 1px solid currentColor; }
}
```
```

## 4. `reference/harden.md` — 「## Testing Strategies」之前插整節（2026-07-10，源 vercel-labs/web-interface-guidelines，MIT）

```markdown
<!-- Stan overlay 2026-07-10: this whole section harvested from vercel-labs/web-interface-guidelines (MIT). Re-apply if a plugin update overwrites this file. -->
### Mobile, Theming & Form Resilience

**Mobile & touch**:
- `touch-action: manipulation` on buttons/links/controls — kills the double-tap zoom delay
- `-webkit-tap-highlight-color: transparent` when you provide your own pressed state
- `overscroll-behavior: contain` on scrollable overlays, drawers, and modals — stops scroll chaining to the page behind
- While dragging: disable text selection (`user-select: none`) and mark the dragged element's content `inert`
- `autoFocus` only on desktop, only one primary input per view; never on mobile (keyboard jump + layout shift)

**Theming & hydration**:
- Dark themes need `color-scheme: dark` on the root — native scrollbars, form controls, and shadows follow
- `<meta name="theme-color">` matching the page background (mobile browser chrome)
- Native `<select>` must get an explicit `background-color` — Windows dark mode renders unreadable defaults otherwise
- Hydration resilience: text typed before hydration must survive; date/locale-dependent rendering must match server and client; no layout shift at hydrate

**Forms & i18n details**:
- `spellcheck="false"` on emails, codes, usernames — red squiggles on valid input look broken
- Explicit `autocomplete` values everywhere; disable it on fields where autofill is actively wrong (search-as-you-type; one-off codes get `one-time-code`)
- `beforeunload` warning when unsaved changes exist — losing form work is the worst dead end
- `translate="no"` on brand names, codes, and technical identifiers (machine translation breaks them)
- `scroll-margin-top` on anchor/heading targets so fixed headers don't swallow them
```
