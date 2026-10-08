from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = REPO_ROOT / 'site' / 'templates' / 'base.html'
CONTENT_CSS = REPO_ROOT / 'site' / 'static' / 'css' / 'content-pages.css'


class BrandAttributionAccessibilityTest(TestCase):
    def test_parent_label_is_plain_text_and_header_stack_stays_compact(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        css = CONTENT_CSS.read_text(encoding='utf-8')

        self.assertIn('<span class="brand__parent">A Quollnet product</span>', template)
        self.assertNotIn('<a class="brand__parent"', template)
        self.assertNotIn('row-gap: 8px;', css)
        self.assertNotIn('min-height: 24px;', css)
