from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_CSS = REPO_ROOT / 'site' / 'static' / 'css' / 'site.css'
BASE_TEMPLATE = REPO_ROOT / 'site' / 'templates' / 'base.html'


class PublicAccessibilityTest(TestCase):
    def test_eyebrow_uses_accessible_light_mode_color(self):
        css = SITE_CSS.read_text(encoding='utf-8')
        self.assertIn('--eyebrow: #876A42;', css)
        self.assertIn('color: var(--eyebrow);', css)
        self.assertIn('--eyebrow: #CDB58A;', css)

    def test_brand_logo_link_has_accessible_home_label(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        self.assertIn(
            '<a class="brand__logo-link" href="/" aria-label="CashflowPot home">',
            template,
        )
