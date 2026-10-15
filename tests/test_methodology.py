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
        self.assertIn('quick to revise when the project changes', html)

    def test_page_follows_current_calculation_sequence(self):
        html = self._html()

        for concept in (
            'Main-contract inflow',
            'Independent contract curve',
            'Activity-linked inflow',
            'Work Activity outflow',
            'Scheduled Cost outflow',
            'Financing facilities',
            'Cash position',
            'Contract-value work',
            'Project Cashflow',
        ):
            self.assertIn(concept, html)

        for formula in (
            'Value factor = Contract value / Total Work Activity cost',
            'Net cash flow = Total inflow − Total outflow',
            'Σ Work Activity outflow = Work Activity estimated cost',
            'Σ Scheduled Cost outflow = Scheduled Cost total',
        ):
            self.assertIn(formula, html)

    def test_page_explains_wieb_as_forecasting_assumption(self):
        html = self._html()

        self.assertIn('Work in Excess of Billings (WIEB)', html)
        self.assertIn('forecasting assumption', html)
        self.assertIn('share of completed work not billed in the current period', html)
        self.assertIn('carry part of each period', html)
        self.assertIn('into the next period', html)
        self.assertIn('Direct cost is paid as incurred', html)
        self.assertIn('WIEB changes timing, not lifetime value', html)

    def test_page_explains_activity_linked_value_factor_without_sov_roadmap(self):
        html = self._html()

        self.assertIn('combined Work Activity cost-work profile is scaled proportionally to contract value', html)
        self.assertIn('Neither method assigns individual selling prices or a Schedule of Values to Activities', html)
        self.assertIn('Scheduled Cost is excluded from both the Work-cost denominator and the contract-value work profile', html)
        self.assertNotIn('Activity-specific selling value and markup allocation', html)
        self.assertNotIn('planned extension', html)

    def test_page_exposes_model_invariants_and_limits(self):
        html = self._html()

        for invariant in (
            'Σ Work Activity work = Work Activity estimated cost',
            'Σ Work Activity outflow = Work Activity estimated cost',
            'Σ Scheduled Cost work = 0',
            'Σ Scheduled Cost outflow = Scheduled Cost total',
            'Σ Project inflow = Contract value',
        ):
            self.assertIn(invariant, html)

        self.assertIn('forecast, not a guarantee', html)
        self.assertIn('time-phased work or cost', html)
        self.assertIn('mathematical execution profile', html)
        self.assertNotIn('CashflowPot does not replace Primavera P6', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('href="/how-it-works/"', html)