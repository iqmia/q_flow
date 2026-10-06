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
        self.assertIn('From the project information you know to the cash decision you need.', html)

    def test_page_explains_the_six_step_workflow(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / 'how-it-works' / 'index.html').read_text(encoding='utf-8')

        for heading in (
            'Define the project',
            'Set the inflow forecast method',
            'Build the activity forecast',
            'Apply contract terms and assumptions',
            'Review the forecast',
            'Revise scenarios and export',
        ):
            self.assertIn(heading, html)

        for concept in (
            'Contract value',
            'Independent contract curve',
            'Activity-linked inflow',
            'Retention',
            'Payment period',
            'WIEB',
            'subcontracted share',
            'Peak negative cash',
            'working capital',
            'lender review',
            'mid-project reforecast',
        ):
            self.assertIn(concept, html)

    def test_page_sets_ai_and_product_boundaries(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / 'how-it-works' / 'index.html').read_text(encoding='utf-8')

        self.assertIn('AI-assisted project setup is in development', html)
        self.assertIn('CashflowPot calculation engine remains responsible for the forecast', html)
        self.assertIn('detailed programme can inform activity timing', html)
        self.assertIn('does not require a detailed programme for every cash decision', html)
        self.assertNotIn('CashflowPot does not replace Primavera P6', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('href="/methodology/"', html)
