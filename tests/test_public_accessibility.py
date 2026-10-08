from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_CSS = REPO_ROOT / 'site' / 'static' / 'css' / 'site.css'
CONTENT_CSS = REPO_ROOT / 'site' / 'static' / 'css' / 'content-pages.css'


class PublicAccessibilityTest(TestCase):
    def test_eyebrow_uses_accessible_light_mode_color(self):
        css = SITE_CSS.read_text(encoding='utf-8')
        self.assertIn('--eyebrow: #876A42;', css)
        self.assertIn('color: var(--eyebrow);', css)
        self.assertIn('--eyebrow: #CDB58A;', css)

    def test_stacked_brand_links_have_touch_spacing(self):
        css = CONTENT_CSS.read_text(encoding='utf-8')
        self.assertIn('row-gap: 8px;', css)
        self.assertIn('min-height: 24px;', css)
