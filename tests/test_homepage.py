import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'
BASE_TEMPLATE = REPO_ROOT / 'site' / 'templates' / 'base.html'


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HomepageTest(TestCase):
    def test_build_generates_public_homepage_with_approved_positioning(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            page = output / 'index.html'
            self.assertTrue(page.is_file())
            html = page.read_text(encoding='utf-8')

        self.assertIn('Turn project execution, contract terms and assumptions into a cash-flow forecast.', html)
        self.assertIn('Build a cash-flow forecast', html)
        self.assertIn('/assets/images/home-hero.webp', html)
        self.assertIn('Independent contract curve', html)
        self.assertIn('Activity-linked inflow', html)
        self.assertIn('Tender &amp; bid/no-bid', html)
        self.assertIn('Contractor financing', html)
        self.assertIn('Lender review', html)
        self.assertIn('Mid-project reforecast', html)
        self.assertIn('Professional output', html)
        self.assertIn('AI-assisted project setup', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('href="/how-it-works/"', html)
        self.assertNotIn('Lightweight by design', html)
        self.assertNotIn('CashflowPot does not replace Primavera P6', html)

    def test_homepage_has_search_metadata_and_accurate_ai_language(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / 'index.html').read_text(encoding='utf-8')

        self.assertIn('<title>Construction Cash-Flow Simulation &amp; Forecasting | CashflowPot</title>', html)
        self.assertIn('<link rel="canonical" href="https://cashflowpot.com/">', html)
        self.assertIn('AI-assisted project setup is in development', html)
        self.assertIn('CashflowPot calculation engine remains responsible for the forecast', html)
        self.assertNotIn('AI-driven platform', html)
        self.assertNotIn('aggregateRating', html)

    def test_shared_header_and_footer_link_cashflowpot_to_quollnet_product_page(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('href="/how-it-works/"', template)
        self.assertIn('href="/methodology/"', template)
        self.assertIn('href="/about/"', template)
        self.assertGreaterEqual(
            template.count('https://quollnet.com/apps/cashflowpot'),
            2,
        )
