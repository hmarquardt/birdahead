# UI quality and accessibility audit

Date: 2026-11-16. Evidence: **observed experiment** (local Worker + Chrome via Playwright) and **measured** production header geometry from the preceding alignment fix. Scope is the Phase 3.1 public application and crawlable pages; no catalog, media, progress or geographic-publication behaviour changed.

## Method

- Runtime: local Worker with the accepted release `5604f569…` (100 species, 589 public assets, seven counties).
- Views: Explore, Migration/discovery, Field Guide (closed and opened card), Practice start, Practice feedback, Practice summary, Downloads, Road Trip, Compare, Progress, About, sign-in dialog, Sources, Privacy and the crawlable Migration page.
- Widths: 360, 390, 768, 1024, 1440 and 1920 px. Anonymous and signed-in (Hank) states, both where applicable: 165 renders (the sign-in dialog exists only for anonymous visitors).
- Per render the browser measured: computed foreground/background contrast with alpha and ancestor opacity composited (WCAG 2.2 AA 1.4.3), target size (2.5.8, 24 px minimum; 44 px reported as advisory), document horizontal overflow and its offenders, clipped text, text below 10 px, accessible names/labels/duplicate ids/heading order/toggle state, and focus-ring presence across four Tab presses.
- Signed-in practice feedback and summary used a bounded API fixture because private endpoints correctly require authentication; every other signed-in view used the local database. No credentials were read or printed.
- Screenshots and the JSON report are ignored private evidence (`experiments/private/ui-audit/`). `tooling/ui_audit.py` reproduces the run.

## Client-reported defects

| Defect | Measured cause | Correction |
| --- | --- | --- |
| Nearly invisible "Photos"/"Sounds" filter text | `.segmented button` used dark-panel text `#eaf0e1` on the page background: **1.08:1**. The Field Guide reused a control styled for the dark practice panel. | The segmented control now has a light-context base (forest text on `--surface`), a dark selected state and a `.learning` override that preserves the original cream-on-dark treatment. Selected state measures 8.9:1. |
| Sign out not vertically centred | Generic `.text-button` padding/margin (fixed in the preceding commit) plus a header row without a shared alignment rule. | Scoped header flex row with `align-items:center`, no offsets; guarded by a unit test. |

## Systemic findings and corrections

| Area | Finding (before) | Correction |
| --- | --- | --- |
| Muted text token | `--muted #758078` measured 3.83:1 on the page, 4.04:1 on panels and 3.55:1 as `.fine`; used 44 times (metadata, captions, scientific names, footer). | `--muted #5b655d`: 5.65:1 page, 5.96:1 panel, 5.33:1 on badges. All muted uses now pass AA. |
| Eyebrow/micro labels | `#718064` at 8–10 px measured 3.94:1; brand tagline 7 px, footer 8–9 px. | `--eyebrow #586649` (5.74:1) and a 10 px minimum text floor across both stylesheets. |
| Unselected tabs | `#7c847c` measured 3.59:1 and wrapped onto two lines at 768 px. | Muted token colour, `white-space:nowrap`, single-line tablet spacing and a horizontal scroll fallback. |
| Undefined tokens | `--ink` (4 uses) and `--sans` silently resolved to `inherit`, so selects ignored their intended colour and the comparison caption rendered serif. | Both defined, plus `--bg`, semantic status colours, radii, type scale and target-size tokens. |
| Status/error colours | Hard-coded error, warning and success hexes duplicated across rules. | `--danger-*`, `--warn-*`, `--success-*` tokens (all ≥4.5:1) used by `.error`, `.gap-label`, `.download-status`. |
| Duplicate/conflicting rules | `.gap-label` defined twice with different colour, padding and size; `.login-form` defined twice; generic `.text-button` offsets; dead `.profile-name` rules. | Consolidated to one definition each; removed dead rules; login inputs are 16 px (prevents mobile zoom) with 44 px height. |
| Button inconsistency | Primary/secondary heights differed by 2 px; radii ranged 6/7/9/12/99 px for equivalent controls; disabled buttons were double-dimmed (`opacity:.5` over muted colours) and showed a wait cursor. | Shared primary/secondary geometry and states, pill/sm/md/lg radius tokens, readable disabled styling, `cursor:not-allowed`. |
| Mobile targets | Date-range slider 16 px tall, heat cells 22 px, modal close 18 px, filter selects 22 px, checkboxes 13 px. | Range 32 px, heat cells 24 px, close 44 px, form controls 40–44 px, checkboxes 18–20 px with full-label hit areas. |
| Horizontal overflow | At 390 px the Road Trip config overflowed 78 px and Migration 3,244 px (406 px filter inputs, 77 px overlay bins) because `1fr` grid tracks and percentage flex children used min-content width. The Explore seasonal select was 198×22 px and widened a 320 px page to 352 px. | `minmax(0,1fr)` tracks, `min-width:0` on labels/controls, grid-based overlay bars with `overflow:hidden`, styled `max-width:100%` selects. Maximum document overflow is now **0 px** at every audited width. |
| Focus visibility | The 4 px-offset ring was clipped inside `overflow:hidden` cards, the asset gallery and the heatmap; static pages had no focus styles at all. | Inset offsets inside clipping containers and mirrored `:focus-visible` styles on the public pages. |
| Dialog semantics | No initial focus, no Escape handling, no focus containment, close button below target size. | Focus moves into the dialog and is restored on close, Tab/Shift-Tab cycle inside the card, Escape closes it, close target 44 px. |
| Migration heatmap rows | A `<button>` wrapped a checkbox (60 nested interactive controls) and the chart exposed `role="img"`/`role="table"` around focusable buttons. | Row label and selection are separate controls; chart/heatmap are labelled `group`s; bars expose `aria-pressed`; heat cells keep descriptive labels. |
| Tab semantics | Active tab only had a class. | `aria-current="page"` on the active tab (plus `aria-pressed` on segmented controls). |
| Heading structure | Downloads cards skipped h1→h3; the practice session had no h1. | Pack titles are h2; the session exposes a screen-reader h1. |
| Deep-link scroll | Sticky mobile tabs could cover a scrolled-to card. | `scroll-padding-top`/`scroll-margin-top` for guide, migration, comparison, downloads and road-trip cards. |
| Static page delivery | The local dev server returned 404 for `/public-pages.css`, so local SEO pages rendered unstyled (production serves it from assets). Public page CSS also lacked focus states and reused the low-contrast muted token. | `/public-pages.css` and `/og-birdahead.png` are served by the local server for parity; the stylesheet mirrors the shared tokens and adds focus/hover/target rules. |


## Results

Anonymous 390 px, same checks before and after the pass:

| View | Contrast findings before | Contrast after | Overflow before | Overflow after |
| --- | --- | --- | --- | --- |
| Explore | 66 | 0 | 0 | 0 |
| Migration | 78 | 0 | 3,244 px | 0 |
| Field Guide | 221 | 0 | 0 | 0 |
| Field Guide (open card) | 241 | 0 | 0 | 0 |
| Practice start/feedback/summary | 68 | 0 | 0 | 0 |
| Downloads | 50 | 0 | 0 | 0 |
| Road Trip | 36 | 0 | 78 px | 0 |
| Compare / Progress / About | 62 | 0 | 0 | 0 |
| Sign-in dialog | 73 | 0 | 0 | 0 |

Final matrix: **165 renders, 0 contrast failures, 0 target-size failures, 0 accessibility findings, 0 text below 10 px, 0 unintended horizontal overflow.** The only audit notes are the expected absence of a sign-in trigger while signed in (the dialog is anonymous-only) and data-dense chart cells discussed below.

## Regression checks

- `tests/test_ui_tokens.py` (runs in `uv run python -m unittest discover -s tests`): shared token parity between the app and public stylesheets, no undefined custom properties, 10 px text floor, contrast thresholds for the muted/eyebrow/status/button pairs, the segmented-control light/dark split and the header sign-out alignment contract.
- `tooling/ui_audit.py`: browser sweep of every view at the six widths with the same measurements, writing private screenshots and a JSON report; exits non-zero on any defect or token drift. Requires a local server and Chrome.

```bash
npm run build --prefix app
cd app && BIRDAHEAD_PORT=8799 npx tsx server.ts &
uv run --with playwright python -m tooling.ui_audit --quick   # 390/1440; omit --quick for all six widths
```

## Remaining limitations (proposal, not accepted changes)

- **Data-dense charts.** Migration bar and heatmap cells are 2–5 px wide by 24 px tall. They are keyboard reachable, labelled and supplementary: species selection, the date-range slider and the heatmap label buttons provide equivalent larger controls. This is documented as a deliberate dense-data trade-off, not a claim of full 2.5.8 conformance.
- **Tab strip.** Below 751 px the navigation scrolls horizontally with a visible scrollbar; all tabs remain keyboard reachable, but there is no overflow affordance beyond the scrollbar.
- **Signed-in practice states** were audited with a bounded fixture; a live authenticated browser run remains an operator check because private endpoints require credentials.
- **Assistive technology and physical devices.** Automated DOM checks and Chrome rendering were used; VoiceOver/TalkBack and real-device passes remain deferred, consistent with the existing physical-device deferral.
- **320 px.** The required matrix starts at 360 px. The known Explore select overflow at 320 px is fixed, but no full 320 px sweep was added.
- **Screenshot stitching.** Full-page captures can draw the sticky mobile tab bar over content; judgement used viewport captures for the affected areas.
- **Dormant dark panel.** The `.learning` panel styles are retained (with the segmented override) to preserve the visual identity even though the current Explore composition no longer renders that panel.

