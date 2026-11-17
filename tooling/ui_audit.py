"""Browser-based UI quality regression check for the public BirdAhead app.

Renders every application view and the crawlable public pages at six widths with
Chrome, then measures WCAG contrast, target size, layout overflow, typography and
accessibility invariants on the real DOM. Screenshots and a JSON report land in
ignored private storage (experiments/private/ui-audit/).

Usage (local, bounded):
    npm run build --prefix app
    cd app && BIRDAHEAD_PORT=8799 npx tsx server.ts &
    uv run --with playwright python -m tooling.ui_audit --quick

Exit code 1 means at least one measurable defect was found. The check never
touches production, credentials or learner data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - operator tool
    print("Playwright is required: uv run --with playwright python -m tooling.ui_audit --quick", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/private/ui-audit"
WIDTHS = [(360, 800), (390, 844), (768, 1024), (1024, 768), (1440, 900), (1920, 1080)]

AUDIT_JS = r"""
() => {
  const sel = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) return s + '#' + el.id;
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 3) : [];
    if (cls.length) s += '.' + cls.join('.');
    return s;
  };
  const describe = (el) => {
    const parts = [sel(el)];
    let n = el.parentElement, depth = 0;
    while (n && n !== document.body && depth < 2) { parts.push(sel(n)); n = n.parentElement; depth++; }
    return parts.reverse().join(' > ');
  };
  const visible = (el) => {
    if (!el.getClientRects().length) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0.5 && r.height > 0.5;
  };
  const parseColor = (value) => {
    const m = String(value).match(/^rgba?\(([^)]+)\)$/);
    if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const blend = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  const alphaOf = (el) => { let a = 1, n = el; while (n && n.nodeType === 1) { a *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; } return a; };
  const bgOf = (el) => {
    const layers = []; let complex = false; let n = el;
    while (n && n.nodeType === 1) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') complex = true;
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0) layers.push(c);
      n = n.parentElement;
    }
    let bg = parseColor(getComputedStyle(document.documentElement).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
    if (bg.a < 1) bg = blend(bg, { r: 255, g: 255, b: 255, a: 1 });
    for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
    return { bg, complex };
  };
  const skipTags = new Set(['SCRIPT', 'STYLE', 'SVG', 'PATH', 'CIRCLE', 'RECT', 'LINE', 'POLYLINE', 'IMG', 'VIDEO', 'AUDIO', 'CANVAS']);
  const contrast = [];
  const tiny = new Map();
  const checkText = (el, text, cs, opts = {}) => {
    const fg0 = parseColor(cs.color);
    if (!fg0) return;
    const { bg, complex } = bgOf(el);
    const fg = blend({ ...fg0, a: fg0.a * alphaOf(el) }, bg);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const need = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
    const r = ratio(fg, bg);
    const disabled = !!el.closest('button:disabled,[disabled],[aria-disabled="true"]');
    if (!complex && !disabled && r + 0.01 < need) {
      contrast.push({ where: describe(el), text: String(text).slice(0, 70), ratio: +r.toFixed(2), need,
        size: +size.toFixed(1), color: cs.color,
        bg: 'rgb(' + Math.round(bg.r) + ', ' + Math.round(bg.g) + ', ' + Math.round(bg.b) + ')', ...opts });
    }
    if (size < 10) {
      const key = describe(el) + '|' + size.toFixed(1);
      const row = tiny.get(key) || { where: describe(el), size: +size.toFixed(1), count: 0, sample: String(text).slice(0, 40) };
      row.count += 1; tiny.set(key, row);
    }
  };
  for (const el of document.body.querySelectorAll('*')) {
    if (skipTags.has(el.tagName)) continue;
    if (el.closest('.sr-only') || el.closest('[aria-hidden="true"]')) continue;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) continue;
    const text = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(' ').replace(/\s+/g, ' ').trim();
    if (!text || !visible(el)) continue;
    checkText(el, text, getComputedStyle(el));
  }
  for (const el of document.querySelectorAll('input:not([type="hidden"]), select, textarea')) {
    if (!visible(el)) continue;
    const value = el.tagName === 'SELECT' ? (el.selectedOptions[0]?.textContent || '') : el.value;
    if (String(value).trim()) checkText(el, value, getComputedStyle(el), { control: el.tagName.toLowerCase() });
  }

  const scrollableX = (el) => {
    for (let n = el.parentElement; n; n = n.parentElement) {
      if (/(auto|scroll)/.test(getComputedStyle(n).overflowX)) return true;
    }
    return false;
  };
  const dense = (el) => !!el.closest('.migration-chart-bars, .migration-heat-cells');
  const targets = [];
  for (const el of document.querySelectorAll('button, a[href], input:not([type="hidden"]), select, textarea, [role="button"]')) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    if (el.tagName === 'A' && cs.display === 'inline' && !/(primary|secondary|chip|button)/.test(String(el.className))) continue;
    let rectEl = el;
    if (/^(checkbox|radio)$/.test(el.type || '') && el.labels && el.labels.length) rectEl = el.labels[0];
    const r = rectEl.getBoundingClientRect();
    const label = String(el.innerText || el.value || el.getAttribute('aria-label') || el.tagName).trim().replace(/\s+/g, ' ').slice(0, 45);
    const scroller = scrollableX(el);
    const inside = scroller || (r.right <= innerWidth + 1 && r.left >= -1);
    const minSide = Math.min(r.width, r.height);
    const record = { where: describe(el), label, w: Math.round(r.width), h: Math.round(r.height), inside,
      exempt: dense(el) ? 'data-dense-chart' : undefined };
    if (record.exempt || scroller) { if (minSide < 44) targets.push({ level: 'advisory', ...record }); continue; }
    if (minSide < 24 || !inside) targets.push({ level: 'fail', ...record });
    else if (minSide < 44) targets.push({ level: 'advisory', ...record });
  }

  const a11y = [];
  const named = (el) => (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.innerText || el.textContent || '').trim();
  for (const el of document.querySelectorAll('button, a[href], [role="button"]')) {
    if (visible(el) && !named(el)) a11y.push({ rule: 'accessible-name', where: describe(el) });
  }
  for (const img of document.querySelectorAll('img')) {
    if (!img.hasAttribute('alt')) a11y.push({ rule: 'image-alt', where: describe(img) });
  }
  for (const el of document.querySelectorAll('input:not([type="hidden"]), select, textarea')) {
    if (!((el.labels && el.labels.length) || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))) {
      a11y.push({ rule: 'form-label', where: describe(el) });
    }
  }
  const ids = new Map();
  for (const el of document.querySelectorAll('[id]')) ids.set(el.id, (ids.get(el.id) || 0) + 1);
  for (const [id, count] of ids) if (count > 1) a11y.push({ rule: 'duplicate-id', where: '#' + id });
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible).map((h) => Number(h.tagName[1]));
  headings.forEach((level, index) => {
    if (index === 0 && level > 1) a11y.push({ rule: 'heading-start', level });
    if (index > 0 && level - headings[index - 1] > 1) a11y.push({ rule: 'heading-skip', from: headings[index - 1], to: level });
  });
  if (!headings.includes(1)) a11y.push({ rule: 'page-h1', where: 'document' });
  for (const el of document.querySelectorAll('button button, button input, button select, button a[href], a[href] button, a[href] a[href]')) {
    if (visible(el)) a11y.push({ rule: 'nested-interactive', where: describe(el) });
  }
  for (const el of document.querySelectorAll('button')) {
    if (!visible(el)) continue;
    const stateful = el.classList.contains('selected') || el.classList.contains('active') || el.classList.contains('correct') || el.classList.contains('incorrect');
    if (stateful && !el.hasAttribute('aria-pressed') && !el.hasAttribute('aria-current') && !el.hasAttribute('aria-selected')) {
      a11y.push({ rule: 'toggle-state', where: describe(el) });
    }
  }

  const overflowX = document.documentElement.scrollWidth - innerWidth;
  const offenders = [];
  if (overflowX > 1) {
    for (const el of document.body.querySelectorAll('*')) {
      if (!visible(el) || scrollableX(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.right > innerWidth + 1 || r.left < -1) {
        offenders.push({ where: describe(el), left: Math.round(r.left), right: Math.round(r.right) });
        if (offenders.length >= 8) break;
      }
    }
  }
  const clipped = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (!visible(el) || skipTags.has(el.tagName) || el.closest('.sr-only')) continue;
    const cs = getComputedStyle(el);
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    if (/(hidden|clip)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 2) clipped.push({ kind: 'vertical', where: describe(el) });
    if (/(hidden|clip)/.test(cs.overflowX) && el.scrollWidth > el.clientWidth + 2 && cs.textOverflow !== 'ellipsis') clipped.push({ kind: 'horizontal', where: describe(el) });
  }
  return {
    url: location.href, width: innerWidth, contrast, targets, a11y, overflowX, offenders, clipped,
    tiny: [...tiny.values()].sort((a, b) => a.size - b.size || b.count - a.count),
    height: document.documentElement.scrollHeight,
  };
}
"""



def start_practice(page, kind: str = "photo"):
    page.get_by_role("button", name=f"Start {kind} practice").click()
    page.wait_for_selector(".practice-media", timeout=25000)


def answer_once(page):
    start_practice(page)
    page.locator(".choice-grid button").first.click()
    page.wait_for_selector(".feedback", timeout=15000)


def finish_practice(page, count: int = 10):
    start_practice(page)
    for _ in range(count):
        if not page.locator(".choice-grid button").count():
            break
        page.locator(".choice-grid button").first.click()
        page.wait_for_selector(".feedback", timeout=15000)
        advance = page.get_by_role("button", name="Next example")
        if not advance.count():
            break
        advance.click()
        page.wait_for_timeout(120)
        if page.locator(".stats").count():
            break
    page.wait_for_selector(".practice-shell .stats", timeout=25000)


def open_first_species(page):
    page.wait_for_selector(".species-card", timeout=25000)
    page.locator(".species-card .species-head").first.click()
    page.wait_for_selector(".asset-gallery", timeout=15000)


def open_login(page):
    page.get_by_role("button", name="Household sign in").click()
    page.wait_for_selector(".modal-card", timeout=10000)


VIEWS = [
    ("explore", "?tab=explore", None),
    ("migration", "?tab=migration", None),
    ("guide", "?tab=guide", None),
    ("guide-open", "?tab=guide", open_first_species),
    ("practice-start", "?tab=practice", None),
    ("practice-feedback", "?tab=practice", answer_once),
    ("practice-summary", "?tab=practice", finish_practice),
    ("downloads", "?tab=downloads", None),
    ("roadtrip", "?tab=roadtrip", None),
    ("compare", "?tab=compare", None),
    ("progress", "?tab=progress", None),
    ("about", "?tab=about", None),
    ("login-modal", "?tab=explore", open_login),
    ("sources-page", "/sources", None),
    ("privacy-page", "/privacy", None),
    ("migration-page", "/migration", None),
]

NARROW_VIEWS = {"guide-open", "practice-feedback", "practice-summary", "login-modal"}



def run(base_url: str, widths, label: str, guest_only: bool) -> list[dict]:
    results = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:  # fall back to Playwright's bundled Chromium
            browser = p.chromium.launch(headless=True)
        for width, height in widths:
            for view, query, action in VIEWS:
                if width not in (360, 390, 1440) and view in NARROW_VIEWS:
                    continue
                if not guest_only and view in {"login-modal", "practice-feedback", "practice-summary"}:
                    continue
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
                page = context.new_page()
                if not guest_only:
                    page.route(
                        "**/api/session",
                        lambda route: route.fulfill(status=200, content_type="application/json",
                                                    body=json.dumps({"profile_id": "hank", "name": "Hank"})),
                    )
                page.goto(base_url + (query if query.startswith("/") else "/" + query), wait_until="domcontentloaded")
                page.wait_for_selector(".site-header, main.page" if query.startswith("/") else ".topbar .profile", timeout=25000)
                page.wait_for_timeout(800)
                if action:
                    try:
                        action(page)
                        page.wait_for_timeout(600)
                    except Exception as exc:  # keep auditing other views
                        results.append({"view": view, "width": width, "actionError": str(exc)[:200]})
                        print(f"ACTION-ERROR {width} {view}: {type(exc).__name__}: {str(exc)[:120]}")
                data = page.evaluate(AUDIT_JS)
                shot = OUTPUT / label / f"{width}-{view}.png"
                page.screenshot(path=str(shot), full_page=True, animations="disabled")
                data.update({"view": view, "width": width, "screenshot": str(shot)})
                results.append(data)
                failures = sum(1 for t in data["targets"] if t["level"] == "fail")
                print(f"{width:5} {view:17} contrast={len(data['contrast']):3} targetfails={failures:2} "
                      f"a11y={len(data['a11y']):2} tiny={len(data['tiny']):2} overflowX={data['overflowX']}")
                context.close()
        browser.close()
    return results




def token_drift() -> dict:
    def block(path: Path) -> dict[str, str]:
        import re
        text = path.read_text()
        match = re.search(r":root\s*\{(.*?)\n\}", text, re.S)
        return {} if not match else {name: " ".join(value.split()) for name, value in
                                     re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", match.group(1))}

    app = block(ROOT / "app/src/style.css")
    public = block(ROOT / "app/public/public-pages.css")
    return {name: (app.get(name), public.get(name)) for name in sorted(set(app) | set(public)) if app.get(name) != public.get(name)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8799")
    parser.add_argument("--quick", action="store_true", help="only 390 and 1440 px")
    parser.add_argument("--guest-only", action="store_true")
    args = parser.parse_args()
    widths = [(390, 844), (1440, 900)] if args.quick else WIDTHS
    label = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    OUTPUT.joinpath(label).mkdir(parents=True, exist_ok=True)
    print(f"Auditing {args.base_url} at {', '.join(str(w) for w, _ in widths)} px")
    results = run(args.base_url, widths, label, args.guest_only)
    drift = token_drift()
    results.append({"view": "shared-tokens", "width": 0, "drift": drift})
    failures = [row for row in results if row.get("contrast") or row.get("tiny") or row.get("overflowX", 0) > 1
                or row.get("a11y") or any(t["level"] == "fail" for t in row.get("targets", []))
                or row.get("actionError") or row.get("clipped")]
    report = OUTPUT / f"report-{label}.json"
    report.write_text(json.dumps(results, indent=1))
    if drift:
        print("TOKEN DRIFT:", json.dumps(drift, indent=1))
    print(f"{len(results) - 1} renders, {len(failures)} with defects; screenshots in {OUTPUT / label}")
    print(f"report: {report}")
    return 1 if failures or drift else 0


if __name__ == "__main__":
    sys.exit(main())
