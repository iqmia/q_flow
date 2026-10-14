import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder_current', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_page(relative_path: str):
    module = _load_builder()
    temp_dir = tempfile.TemporaryDirectory()
    output = module.build_site(Path(temp_dir.name) / 'site-output')
    html = (output / relative_path).read_text(encoding='utf-8')
    return temp_dir, html


class CurrentProductSiteTest(TestCase):
    def test_home_presents_activity_modes_financing_and_current_kpis(self):
        temp_dir, html = _build_page('index.html')
        try:
            folded = html.casefold()
            for token in (
                'Work activities',
                'Scheduled Cost',
                'financing facilities',
                'Peak Funding Requirement',
                'Peak Facility Usage',
                'Outstanding Facilities',
                'Cash after Debt Settlement',
                'Project Cashflow',
                'Facilities',
                'Cash Position',
            ):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_how_it_works_includes_scheduled_cost_and_financing_steps(self):
        temp_dir, html = _build_page('how-it-works/index.html')
        try:
            folded = html.casefold()
            for token in (
                'Work activities',
                'Scheduled Cost',
                'Add financing facilities',
                'Project Cashflow',
                'Facilities',
                'Cash Position',
                'Cash after Debt Settlement',
            ):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_methodology_matches_current_activity_and_financing_model(self):
        temp_dir, html = _build_page('methodology/index.html')
        try:
            folded = html.casefold()
            for token in (
                'Work Activity',
                'Scheduled Cost',
                'Manual Work',
                'PPC issued',
                'PPC receipts',
                'revolving',
                'non-revolving',
                'Work duration',
                'Financial horizon',
                'Cash after Debt Settlement',
                'Project Cashflow',
                'Cash Position',
            ):
                self.assertIn(token.casefold(), folded)
            self.assertNotIn(
                'When the balance is negative, the configured financing rate for that model period is applied.',
                html,
            )
        finally:
            temp_dir.cleanup()

    def test_about_mentions_scheduled_cost_and_financing_facilities(self):
        temp_dir, html = _build_page('about/index.html')
        try:
            folded = html.casefold()
            for token in ('Scheduled Cost', 'financing facilities', 'funding requirement'):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_discovery_metadata_lists_current_product_capabilities(self):
        module = _load_builder()
        home = next(page for page in module.PAGES if page.canonical_path == '/')
        structured = module._structured_data_for(home)
        software = next(
            item for item in structured['@graph']
            if item.get('@type') == 'SoftwareApplication'
        )
        feature_list = ' '.join(software['featureList']).casefold()
        for token in (
            'scheduled cost',
            'financing facilities',
            'cash after debt settlement',
            'excel export',
        ):
            self.assertIn(token, feature_list)

        llms = module._render_llms_txt().casefold()
        for token in ('scheduled cost', 'financing facilities', 'cash after debt settlement'):
            self.assertIn(token, llms)
