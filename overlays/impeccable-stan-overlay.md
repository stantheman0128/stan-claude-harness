# impeccable — Stan overlay patch 檔（重貼指引）

plugin 升級會建新版本目錄、不會帶走這些 overlay。**每次 `claude plugin update impeccable` 後，把本檔各段重貼進新版本目錄的對應檔案**（路徑：`~/.claude/plugins/cache/impeccable/impeccable/<新版本>/skills/impeccable/`）。貼完用 `grep -rn "Stan overlay" <新版本目錄>` 驗證 5 個標記行都在（數量也寫在 `overlays/markers.json`，開場的 overlay watch 會比對）。

目前套用於：4.10.0（2026-11-23 重貼；5 個標記行、10 條規則，grep 實測 5，`claude plugin validate` 通過；上游原檔備份在 `4.10.0/.stan-upstream/`）。4.x 大改：bans 從 SKILL.md 搬到 `reference/craft-floor.md` 的「## Refuse」，animate.md 整篇重寫，沒有 NEVER 清單也沒有 reduced-motion CSS 區塊，所以第 1 到 3 段換了位置，第 2、3 段改成 4.x 的寫法；第 4 段位置不變。升級法備註：上游沒動 overlay 所在檔時，用「copy-forward 舊檔」代替手動重貼（3.8.0→3.9.1 用過）；有動就照各段標的錨點重貼。
相關記憶：[[project-impeccable-overlay]]。升級注意：4.10.0 已有原生平台層（reference/ios.md、android.md），平台由 init 記進 PRODUCT.md。原本記的待辦「LINE Notify+ 的 PRODUCT.md 要加 android 平台」格式改照 4.10.0 的 init（2026-11-23 沒查是否已做）。可考慮把 taste 兩條 bans 開 PR 回饋上游（Apache-2.0 相容），成功就少貼半套。

---

## 1. `reference/craft-floor.md`：「## Refuse」清單尾端，接在「- Light or dark picked by category.」那條後面（2026-07-05，源 Leonxlnx/taste-skill，MIT；4.x 以前在 SKILL.md 的 Absolute bans）

```markdown
<!-- Stan overlay 2026-07-05: next 2 bans harvested from Leonxlnx/taste-skill (MIT). Re-apply if a plugin update overwrites this file. -->
- **The Jane Doe effect.** Generic placeholder people (Jane Doe, John Smith, stock-smile avatars) and too-perfect metrics (99.99% uptime, 50% faster, 10x growth) in demo copy. Invent specific, plausible names and jagged numbers (98.7%, 43%), or use real content.
- **The premium-consumer palette rotation.** Beige + brass/gold + oxblood + espresso deployed as a set because the brief says "premium" or "luxury". Every AI-generated luxury site ships this exact skin. Any one of these colors can be right alone; the four-piece uniform is the tell.
```

## 2. `reference/animate.md`：「## Implement to the runtime」節尾，接在「Keep content visible in the default state…」那段後面，前面空一行（2026-07-05＋2026-07-10，源 emilkowalski/skills，MIT）

4.x 以前插在 Accessibility 節的 NEVER 清單裡，句子省略了 NEVER；4.x 沒有那張清單，改成 Don't 開頭：

```markdown
<!-- Stan overlay 2026-07-05: next 2 rules harvested from emilkowalski/skills (MIT). Re-apply if a plugin update overwrites this file. -->
- Don't animate keyboard-initiated or high-frequency actions (100+ times a day: shortcuts, command palettes, tab switches); repetition makes motion feel slow, not smooth.
- Don't enter from `scale(0)`; nothing in the physical world appears from nothing. Use `scale(0.95)` + `opacity: 0` instead.
<!-- Stan overlay 2026-07-10: next 2 rules harvested from emilkowalski/skills (MIT). Re-apply if a plugin update overwrites this file. -->
- Don't scale popovers, dropdowns, or tooltips from the default center origin; set `transform-origin` to the trigger side so they grow from where they came from (Radix exposes `--radix-*-content-transform-origin`). Modals are exempt because they own the screen.
- Don't animate Framer Motion `x`/`y` shorthands for performance-critical motion; independent transforms skip hardware acceleration, so animate the full `transform` string instead.
```

## 3. `reference/animate.md`：「## Accessibility and control」節，接在「Every web animation needs a `prefers-reduced-motion` path…」那段後面，前面空一行（2026-07-10，源 emilkowalski/skills，MIT）

4.x 以前接在 reduced-motion 的 CSS 區塊後面；4.x 那段只剩文字，所以多一行引言，註解裡的節名也跟著換：

```markdown
<!-- Stan overlay 2026-07-10: harvested from emilkowalski/skills (MIT). "Choose material by meaning" above allows backdrop and blur surfaces; these two fallbacks cover the a11y signals those surfaces need. Re-apply if a plugin update overwrites this file. -->
Give glass and backdrop-blur surfaces these fallbacks:

```css
@media (prefers-reduced-transparency: reduce) {
  .glass { backdrop-filter: none; background: var(--surface-solid); }
}
@media (prefers-contrast: more) {
  .glass, .card { border: 1px solid currentColor; }
}
```
```

## 4. `reference/harden.md`：「## Testing Strategies」之前插整節，後面空一行（2026-07-10，源 vercel-labs/web-interface-guidelines，MIT）

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
