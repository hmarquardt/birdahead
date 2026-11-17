# ADR 0012 — shared visual tokens and an accessibility floor

Date: 2026-11-16. Status: accepted as part of the UI quality audit.

The header alignment fix exposed two systemic style problems: a Field Guide control reused dark-panel text on a light background (1.08:1), and the shared muted colour failed AA on every light surface. A full rendered audit of all views at six widths confirmed that these were token and composition problems, not isolated mistakes.

Decision: keep the existing visual identity and consolidate the shared layer instead of restyling the product.

- One semantic token block (colour, status, radius, type scale, target size, focus) is the source of truth in `app/src/style.css`; `app/public/public-pages.css` mirrors it for the crawlable pages. A static test fails on drift.
- Informational text has a 10 px floor; muted and eyebrow colours meet 4.5:1 on every light surface used by the app.
- Interactive controls have a 24 px minimum target and a 44 px comfortable floor on mobile; dense chart cells stay compact because equivalent labelled controls exist, and that trade-off is recorded rather than hidden.
- Component styles are context-specific: the light Field Guide segmented control no longer inherits the dark practice-panel treatment, while the dark-panel variant is preserved explicitly.
- Focus, hover, disabled and selected states are defined for shared controls; dialogs move and contain focus and close on Escape.
- Browser measurement (`tooling/ui_audit.py`) and static token/contrast checks (`tests/test_ui_tokens.py`) are the regression gates. Neither runs in CI yet; the static checks run with the existing Python suite, the browser sweep is a bounded local/operator check.

Scope boundaries: no markup redesign, no new dependencies in the shipped bundle, no change to catalog, media eligibility, progress, privacy or geographic publication. The audit is a quality pass within Phase 3.1, not a commercial or accessibility-certification claim. VoiceOver/TalkBack and physical-device validation remain deferred.
