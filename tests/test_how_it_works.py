import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HowItWorksPageTest(TestCase):
    def test_build_generates_how_it_works_page(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            page = output / 'how-it-works' / 'index.html'
            self.assertTrue(page.is_file())
            html = page.read_text(encoding='utf-8')

        self.assertIn('<title>How CashflowPot Works | Construction Cash-Flow Forecasting</title>', html)
        self.assertIn('<link rel="canonical" href="https://cashflowpot.com/how-it-works/">', html)
        self.assertIn('From project assumptions to a usable cash-flow forecast', html)

    def test_page_explains_the_five_step_workflow(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / 'how-it-works' / 'index.html').read_text(encoding='utf-8')

        for heading in (
            'Define the project',
            'Build the activity forecast',
            'CashflowPot calculates the forecast',
            'Review and adjust scenarios',
            'Export and communicate',
        ):
            self.assertIn(heading, html)

        for concept in (
            'Contract value',
            'Retention',
            'Payment period',
            'WIEB',
            'subcontracted portion',
            'peak negative cash',
            'Tender',
            'Feasibility',
        ):
            self.assertIn(concept, html)

    def test_page_sets_ai_and_product_boundaries(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / 'how-it-works' / 'index.html').read_text(encoding='utf-8')

        self.assertIn('AI-assisted project setup is in development', html)
        self.assertIn('the CashflowPot calculation engine remains responsible for the forecast', html)
        self.assertIn('Primavera P6', html)
        self.assertIn('MS Project', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('href="/methodology/"', html)
