"""Regression checks for shared UI tokens, contrast and the reported style defects.

These are static checks on the stylesheets: they run in the normal Python suite
without a browser and guard the systemic fixes made in the UI quality audit.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "app/src/style.css"
PUBLIC_CSS = ROOT / "app/public/public-pages.css"


def tokens(path: Path) -> dict[str, str]:
    text = path.read_text()
    match = re.search(r":root\s*\{(.*?)\n\}", text, re.S)
    if not match:
        return {}
    return {name: " ".join(value.split()) for name, value in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", match.group(1))}


def rule(path: Path, selector: str) -> str:
    text = path.read_text()
    match = re.search(r"(?:^|\n)" + re.escape(selector) + r"\s*\{([^}]*)\}", text)
    if not match:
        raise AssertionError(f"selector not found: {selector}")
    return match.group(1)


def luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(foreground: str, background: str) -> float:
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


class DesignTokenTests(unittest.TestCase):
    def test_public_stylesheet_mirrors_app_tokens(self):
        app = tokens(APP_CSS)
        public = tokens(PUBLIC_CSS)
        self.assertGreaterEqual(len(app), 20)
        self.assertEqual(app, public, "app/src/style.css and app/public/public-pages.css token blocks drifted")

    def test_every_custom_property_is_defined(self):
        for path in (APP_CSS, PUBLIC_CSS):
            text = path.read_text()
            defined = set(tokens(path))
            used = set(re.findall(r"var\((--[a-z0-9-]+)", text))
            self.assertEqual(sorted(used - defined), [], f"undefined custom properties in {path.name}")

    def test_no_unreadably_small_text(self):
        for path in (APP_CSS, PUBLIC_CSS):
            for size in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", path.read_text()):
                self.assertGreaterEqual(float(size), 10, f"{path.name} declares font-size below the 10px floor")


class ContrastTests(unittest.TestCase):
    """WCAG 2.2 AA thresholds for shared text/background pairs."""

    def setUp(self):
        self.app = tokens(APP_CSS)

    def assertPair(self, foreground: str, background: str, minimum: float = 4.5):
        ratio = contrast(foreground, background)
        self.assertGreaterEqual(round(ratio, 2), minimum, f"{foreground} on {background} is {ratio:.2f}:1")

    def test_muted_text_passes_on_every_light_surface(self):
        muted = self.app["--muted"]
        for surface in ("#f8f7f2", "#fffdf8", "#ffffff", "#f4f6ea", "#edf1e1", "#f0f1e9", "#fafaf6"):
            self.assertPair(muted, surface)

    def test_eyebrow_passes_on_page_and_pill(self):
        self.assertPair(self.app["--eyebrow"], "#f8f7f2")
        self.assertPair(self.app["--eyebrow"], "#fffdf8")
        self.assertPair(self.app["--eyebrow"], "#edf0e1")

    def test_state_colors_keep_contrast(self):
        pairs = {
            "primary text": ("#244331", "#dce9b5"),
            "primary hover": ("#244331", "#e6efce"),
            "secondary text": ("#244c3f", "#fffdf8"),
            "selected segmented": ("#f7f7ed", "#244c3f"),
            "dark panel text": ("#f6f6e9", "#244c3f"),
            "dark panel muted": ("#b9c9bc", "#244c3f"),
            "danger": ("#764527", "#f3e7d9"),
            "warning": ("#7e5524", "#fff4df"),
            "success": ("#456a35", "#edf4e4"),
            "focus ring on page": ("#b47e2a", "#f8f7f2"),
        }
        for label, (foreground, background) in pairs.items():
            minimum = 3 if "ring" in label else 4.5
            with self.subTest(label=label):
                self.assertPair(foreground, background, minimum)


class ReportedDefectTests(unittest.TestCase):
    def test_segmented_control_uses_light_context_colors(self):
        body = rule(APP_CSS, ".segmented button")
        self.assertIn("color: var(--forest)", body)
        self.assertIn("background: var(--surface)", body)
        self.assertNotIn("#eaf0e1", body, "the light Field Guide segmented control must not reuse dark-panel text")

    def test_dark_panel_keeps_its_segmented_override(self):
        body = rule(APP_CSS, ".learning .segmented button")
        self.assertIn("#eaf0e1", body)

    def test_header_auth_control_has_no_positional_offset(self):
        body = rule(APP_CSS, ".topbar .profile .sign-out,\n.topbar .profile .signin-trigger")
        self.assertIn("align-items: center", body)
        self.assertIn("margin: 0", body)

    def test_generic_text_button_no_longer_offsets_controls(self):
        body = rule(APP_CSS, ".text-button")
        self.assertIn("margin: 0", body)


if __name__ == "__main__":
    unittest.main()
