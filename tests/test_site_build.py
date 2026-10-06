import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'
BASE_TEMPLATE = REPO_ROOT / 'site' / 'templates' / 'base.html'
GITIGNORE = REPO_ROOT / '.gitignore'

APPROVED_TOKENS = (
    '#E89A5B',
    '#F7F4EF',
    '#FFFDFC',
    '#30322F',
    '#E5DED4',
    '#181A18',
    '#20221F',
    '#272A26',
    '#454943',
    '#79A58D',
    '#C9796F',
    '#7F9FB2',
    '#8D7047',
    '#CDB58A',
)


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SiteBuildTest(TestCase):
    def test_build_copies_shared_css_and_cleans_stale_output(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'site-output'

            output = module.build_site(output_dir)
            self.assertEqual(output, output_dir)
            self.assertTrue((output / 'assets' / 'css' / 'site.css').is_file())

            stale = output / 'stale.txt'
            stale.write_text('old deployment artifact', encoding='utf-8')
            module.build_site(output_dir)
            self.assertFalse(stale.exists())

    def test_shared_css_matches_approved_cashflowpot_theme(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            css = (output / 'assets' / 'css' / 'site.css').read_text(encoding='utf-8')

        for token in APPROVED_TOKENS:
            self.assertIn(token, css)
        self.assertIn('@media (prefers-color-scheme: dark)', css)

    def test_base_template_exposes_shared_page_blocks_and_brand_attribution(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')

        for block in ('title', 'description', 'canonical_url', 'content'):
            self.assertIn(f'block {block}', template)
        self.assertIn('/assets/css/site.css', template)
        self.assertIn('A Quollnet product', template)
        self.assertIn('Quollnet ecosystem', template)
        self.assertIn('/app/', template)

    def test_build_generates_branded_noindex_404_page(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            page = output / '404.html'
            self.assertTrue(page.is_file())
            html = page.read_text(encoding='utf-8')

        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertIn('<title>Page not found | CashflowPot</title>', html)
        self.assertIn('Page not found', html)
        self.assertIn('The page you’re looking for doesn’t exist or may have moved.', html)
        self.assertIn('href="/"', html)
        self.assertIn('Back to CashflowPot', html)
        self.assertIn('href="/app/"', html)
        self.assertIn('Open app', html)
        self.assertIn('A Quollnet product', html)
        self.assertIn('Quollnet ecosystem', html)

    def test_generated_site_output_is_ignored(self):
        gitignore = GITIGNORE.read_text(encoding='utf-8').splitlines()
        self.assertIn('/site/dist/', gitignore)
