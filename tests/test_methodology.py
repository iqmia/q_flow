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


class MethodologyPageTest(TestCase):
    def _html(self) -> str:
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            page = output / 'methodology' / 'index.html'
            self.assertTrue(page.is_file())
            return page.read_text(encoding='utf-8')

    def test_build_generates_methodology_page_with_metadata(self):
        html = self._html()

        self.assertIn('<title>CashflowPot Methodology | Construction Cash-Flow Model</title>', html)
        self.assertIn('<link rel="canonical" href="https://cashflowpot.com/methodology/">', html)
        self.assertIn('A forecast designed to be revised', html)
        self.assertIn('minutes, not weeks', html)

    def test_page_follows_calculation_sequence(self):
        html = self._html()

        for concept in (
            'Contract side — from work to inflow',
            'Execution side — from activity work to outflow',
            'Net cash and financing',
            'Contract-value work',
            'Project outflow',
            'financing rate',
        ):
            self.assertIn(concept, html)

        for formula in (
            'Value factor = Contract value / Total entered activity cost',
            'Net cash flow = Inflow − Outflow',
            'Project outflow = Σ Activity outflow',
        ):
            self.assertIn(formula, html)

    def test_page_explains_wieb_as_forecasting_assumption(self):
        html = self._html()

        self.assertIn('Work in Excess of Billings (WIEB) assumption (%)', html)
        self.assertIn('share of work performed in a period that is not yet billable', html)
        self.assertIn('carried into the following billing period', html)
        self.assertIn('Self-performed work is not adjusted by WIEB', html)
        self.assertIn('cost is generally incurred when the work is performed', html)

    def test_page_states_current_markup_assumption_and_future_direction(self):
        html = self._html()

        self.assertIn('same contract-value-to-cost factor', html)
        self.assertIn('does not currently store a separate selling value for each activity', html)
        self.assertIn('Activity-specific selling value and markup allocation', html)
        self.assertIn('planned extension', html)

    def test_page_exposes_model_invariants_and_limits(self):
        html = self._html()

        for invariant in (
            'Σ Activity work = Activity estimated cost',
            'Σ Activity outflow = Activity estimated cost',
            'Σ Project inflow = Contract value',
        ):
            self.assertIn(invariant, html)

        self.assertIn('forecast, not a guarantee', html)
        self.assertIn('Primavera P6', html)
        self.assertIn('MS Project', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('href="/how-it-works/"', html)
