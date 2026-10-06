import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / 'site' / 'build_site.py'
BASE_TEMPLATE = REPO_ROOT / 'site' / 'templates' / 'base.html'
GITIGNORE = REPO_ROOT / '.gitignore'

APPROVED_TOKENS = (
    '#E89A5B', '#F7F4EF', '#FFFDFC', '#30322F', '#E5DED4',
    '#181A18', '#20221F', '#272A26', '#454943', '#79A58D',
    '#C9796F', '#7F9FB2', '#8D7047', '#CDB58A',
)


def _load_builder():
    spec = importlib.util.spec_from_file_location('cashflowpot_site_builder', BUILD_SCRIPT)
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


class SiteBuildTest(TestCase):
    def test_build_copies_shared_css_and_cleans_stale_output(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'site-output'
            output = module.build_site(output_dir)
            self.assertEqual(output, output_dir)
            self.assertTrue((output / 'assets' / 'css' / 'site.css').is_file())
            self.assertTrue((output / 'assets' / 'css' / 'content-pages.css').is_file())
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
        self.assertIn('/assets/css/content-pages.css', template)
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

    def test_build_generates_all_public_pages(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            for relative_path in (
                'index.html', 'how-it-works/index.html', 'methodology/index.html',
                'about/index.html', 'contact/index.html', 'privacy/index.html',
                'terms/index.html', '404.html',
            ):
                self.assertTrue((output / relative_path).is_file(), relative_path)

    def test_shared_shell_contains_logo_primary_nav_and_footer_links(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        for token in (
            '/app/icons/Icon-192.png', '/app/icons/quollnet_logo_transp.webp',
            'href="/"', 'href="/how-it-works/"',
            'href="/methodology/"', 'href="/about/"', 'href="/app/"',
            'href="/contact/"', 'href="/privacy/"', 'href="/terms/"',
            'https://quollnet.com/apps/cashflowpot',
            'CashflowPot is part of the Quollnet ecosystem for engineering and construction.',
            'Explore CashflowPot on Quollnet',
        ):
            self.assertIn(token, template)

    def test_shared_shell_uses_existing_cashflowpot_app_icon(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        self.assertIn('/app/icons/Icon-192.png', template)

    def test_brand_keeps_logo_beside_stacked_product_and_parent_labels(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        self.assertIn('class="brand__logo-link"', template)
        self.assertIn('class="brand__name" href="/"', template)
        self.assertIn('class="brand__parent"', template)

    def test_shared_css_supports_logo_footer_groups_and_small_screens(self):
        page_css = (REPO_ROOT / 'site' / 'static' / 'css' / 'content-pages.css').read_text(encoding='utf-8')
        for token in (
            '.brand__logo', '.site-footer__groups', '.site-footer__group',
            '.site-footer__quollnet-logo', '.contact-card__icon',
            '.legal-content', '@media (max-width: 760px)', '.site-nav__link',
            '.button--primary',
        ):
            self.assertIn(token, page_css)

    def test_home_positions_cashflowpot_as_cashflow_decision_tool(self):
        temp_dir, html = _build_page('index.html')
        try:
            folded = html.casefold()
            for token in (
                'Independent contract curve', 'Activity-linked inflow', 'contract terms',
                'assumptions', 'balanced S-curve', 'working capital', 'Tender', 'bid',
                'financing', 'lender', 'mid-project', 'reforecast',
            ):
                self.assertIn(token.casefold(), folded)
            for forbidden in ('CashflowPot does not replace Primavera P6', 'Lightweight by design', 'Billing Deferral'):
                self.assertNotIn(forbidden, html)
        finally:
            temp_dir.cleanup()

    def test_how_it_works_explains_both_inflow_methods_and_terms(self):
        temp_dir, html = _build_page('how-it-works/index.html')
        try:
            folded = html.casefold()
            for token in (
                'Independent contract curve', 'Activity-linked inflow', 'contract terms',
                'assumptions', 'balanced S-curve', 'working capital', 'Define the project',
                'Set the inflow forecast method', 'Build the activity forecast',
                'Apply contract terms and assumptions', 'Review the forecast',
                'Revise scenarios and export', 'Payment period', 'WIEB', 'DLP',
                'detailed programme',
            ):
                self.assertIn(token.casefold(), folded)
            for forbidden in ('CashflowPot does not replace Primavera P6', 'Lightweight by design', 'Billing Deferral'):
                self.assertNotIn(forbidden, html)
        finally:
            temp_dir.cleanup()

    def test_methodology_explains_execution_terms_and_cash_position(self):
        temp_dir, html = _build_page('methodology/index.html')
        try:
            folded = html.casefold()
            for token in (
                'A forecast designed to be revised', 'Execution model', 'contract terms',
                'forecasting assumptions', 'Cash position', 'Work in Excess of Billings (WIEB)',
                'Payment period', 'Defects Liability Period (DLP)',
            ):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_methodology_explains_independent_and_activity_linked_inflow(self):
        temp_dir, html = _build_page('methodology/index.html')
        try:
            folded = html.casefold()
            for token in ('Independent contract curve', 'Activity-linked inflow', 'Back-loaded', 'Balanced', 'Front-loaded'):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_methodology_removes_obsolete_sov_roadmap_claim(self):
        temp_dir, html = _build_page('methodology/index.html')
        try:
            for token in ('Activity-specific selling value and markup allocation', 'planned extension', 'CashflowPot does not replace Primavera P6'):
                self.assertNotIn(token, html)
        finally:
            temp_dir.cleanup()

    def test_about_page_has_brand_positioning_and_canonical_url(self):
        temp_dir, html = _build_page('about/index.html')
        try:
            folded = html.casefold()
            for token in ('https://cashflowpot.com/about/', 'A forecast designed to be revised', 'https://quollnet.com/apps/cashflowpot', 'Tender', 'financing', 'lender', 'mid-project'):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_contact_page_uses_only_approved_quollnet_channels(self):
        temp_dir, html = _build_page('contact/index.html')
        try:
            for token in (
                'https://www.quollnet.com',
                'https://www.facebook.com/people/Quollnet/100086014988886/',
                'https://www.instagram.com/quollnet/', 'https://twitter.com/quollnet',
                'https://www.linkedin.com/in/quollnet/', 'https://www.youtube.com/@quollnet',
                'https://wa.me/351911747738', 'Quoll Unipessoal LDA',
            ):
                self.assertIn(token, html)
            self.assertNotIn('mailto:', html)
        finally:
            temp_dir.cleanup()

    def test_contact_page_uses_existing_app_social_icons(self):
        temp_dir, html = _build_page('contact/index.html')
        try:
            for icon_path in (
                '/app/icons/quollnet_logo_transp.webp',
                '/app/icons/facebook.png',
                '/app/icons/insta.png',
                '/app/icons/linkedin.png',
                '/app/icons/twitter.png',
                '/app/icons/wa.png',
                '/app/icons/youtube.png',
            ):
                self.assertIn(icon_path, html)
        finally:
            temp_dir.cleanup()

    def test_privacy_page_identifies_operator_and_expected_sections(self):
        temp_dir, html = _build_page('privacy/index.html')
        try:
            folded = html.casefold()
            for token in (
                'https://cashflowpot.com/privacy/', 'Quollnet', 'Quoll Unipessoal LDA',
                'CashflowPot is a Quollnet product operated by Quoll Unipessoal LDA.',
                'Last updated', 'Information we collect', 'How we use information',
                'Service providers', 'Data retention', 'Security', 'Your rights',
                'Changes to this notice',
            ):
                self.assertIn(token.casefold(), folded)
            for forbidden in ('we never log', 'we never transfer', '100% secure', 'guarantee security'):
                self.assertNotIn(forbidden.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_terms_page_identifies_operator_and_forecast_disclaimer(self):
        temp_dir, html = _build_page('terms/index.html')
        try:
            folded = html.casefold()
            for token in (
                'https://cashflowpot.com/terms/', 'Quollnet', 'Quoll Unipessoal LDA',
                'CashflowPot is a Quollnet product operated by Quoll Unipessoal LDA.',
                'Last updated', 'Account responsibility', 'Acceptable use', 'contract terms',
                'forecasting assumptions', 'not guarantees of actual future cash flows',
                'professional', 'commercial', 'financing decisions', 'Privacy',
            ):
                self.assertIn(token.casefold(), folded)
        finally:
            temp_dir.cleanup()

    def test_public_site_has_no_legacy_article_links_or_obsolete_product_copy(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            html = '\n'.join(page.read_text(encoding='utf-8') for page in output.rglob('*.html'))
        for forbidden in (
            '/article/construction_cashflow_prediction',
            '/article/How_to_Create_a_Project_Cash_Flow_for_Contractors',
            '/article/Quollnet_cashflow',
            '/article/master_construction_project_cashflow_with_cashflowpot',
            'Billing Deferral', 'Activity-specific selling value and markup allocation',
            'CashflowPot does not replace Primavera P6',
            'use_independent_inflow_curve', 'inflow_curve_type', 'inflow_curve_skew',
        ):
            self.assertNotIn(forbidden, html)
        folded = html.casefold()
        for required in ('Independent contract curve', 'Activity-linked inflow', 'contract terms', 'forecasting assumptions'):
            self.assertIn(required.casefold(), folded)
