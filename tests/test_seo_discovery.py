import importlib.util
import html as html_lib
import tempfile
from pathlib import Path
from unittest import TestCase

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'

EXPECTED = {
    'index.html': (
        'Construction Cash-Flow Simulation & Forecasting | CashflowPot',
        'Simulate construction project cash flow from execution timing, contract terms and forecasting assumptions for tendering, financing, lender review, budgeting and project reforecasting.',
        'https://cashflowpot.com/',
    ),
    'how-it-works/index.html': (
        'How CashflowPot Works | Construction Cash-Flow Forecasting',
        'See how CashflowPot combines execution timing, contract terms and assumptions to simulate construction project inflow, outflow, working capital and funding requirements.',
        'https://cashflowpot.com/how-it-works/',
    ),
    'methodology/index.html': (
        'CashflowPot Methodology | Construction Cash-Flow Model',
        'Understand how CashflowPot separates execution, contract terms and forecasting assumptions to calculate project inflow, outflow, net cash and funding requirements.',
        'https://cashflowpot.com/methodology/',
    ),
    'about/index.html': (
        'About CashflowPot | Construction Cash-Flow Simulation',
        'CashflowPot is a focused construction cash-flow simulation and forecasting product for tendering, financing, lender review, portfolio capacity and project reforecasting.',
        'https://cashflowpot.com/about/',
    ),
    'contact/index.html': (
        'Contact CashflowPot | Quollnet',
        'Contact the Quollnet team for CashflowPot product questions, feedback and support.',
        'https://cashflowpot.com/contact/',
    ),
    'privacy/index.html': (
        'Privacy Notice | CashflowPot',
        'Privacy information for CashflowPot, a Quollnet product operated by Quoll Unipessoal LDA.',
        'https://cashflowpot.com/privacy/',
    ),
    'terms/index.html': (
        'Terms of Use | CashflowPot',
        'Terms of use for CashflowPot, a Quollnet product operated by Quoll Unipessoal LDA.',
        'https://cashflowpot.com/terms/',
    ),
}


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SeoMetadataTest(TestCase):
    def test_indexable_pages_have_consistent_search_and_social_metadata(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            for relative_path, (title, description, url) in EXPECTED.items():
                html = (output / relative_path).read_text(encoding='utf-8')
                self.assertIn(f'<title>{title}</title>', html)
                self.assertIn(f'<meta name="description" content="{html_lib.escape(description, quote=True)}">', html)
                self.assertIn(f'<link rel="canonical" href="{url}">', html)
                self.assertIn('<meta name="robots" content="index, follow">', html)
                self.assertIn('<meta property="og:site_name" content="CashflowPot">', html)
                self.assertIn('<meta property="og:type" content="website">', html)
                self.assertIn(f'<meta property="og:title" content="{html_lib.escape(title, quote=True)}">', html)
                self.assertIn(f'<meta property="og:description" content="{html_lib.escape(description, quote=True)}">', html)
                self.assertIn(f'<meta property="og:url" content="{url}">', html)
                self.assertIn('<meta property="og:image" content="https://cashflowpot.com/assets/images/cashflowpot-og.webp">', html)
                self.assertIn('<meta property="og:image:type" content="image/webp">', html)
                self.assertIn('<meta property="og:image:alt" content="CashflowPot construction cash-flow forecasting">', html)
                self.assertIn('<meta name="twitter:card" content="summary_large_image">', html)
                self.assertIn(f'<meta name="twitter:title" content="{html_lib.escape(title, quote=True)}">', html)
                self.assertIn(f'<meta name="twitter:description" content="{html_lib.escape(description, quote=True)}">', html)
                self.assertIn('<meta name="twitter:image" content="https://cashflowpot.com/assets/images/cashflowpot-og.webp">', html)

    def test_404_is_noindex_without_canonical_or_structured_data(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = (output / '404.html').read_text(encoding='utf-8')
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertNotIn('rel="canonical"', html)
        self.assertNotIn('application/ld+json', html)
