import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SITE_DIR / 'templates'
STATIC_DIR = SITE_DIR / 'static'
DEFAULT_OUTPUT_DIR = SITE_DIR / 'dist'
DEFAULT_WEB_ROOT = Path.home() / 'www.cashflowpot.com'
SITE_ORIGIN = 'https://cashflowpot.com'
SOCIAL_IMAGE_URL = f'{SITE_ORIGIN}/assets/images/cashflowpot-og.webp'
ORGANIZATION_ID = f'{SITE_ORIGIN}/#organization'
WEBSITE_ID = f'{SITE_ORIGIN}/#website'
SOFTWARE_ID = f'{SITE_ORIGIN}/#software'
ROOT_DISCOVERY_FILES = ('robots.txt', 'sitemap.xml', 'llms.txt')
QUOLLNET_SOCIAL_URLS = (
    'https://www.facebook.com/people/Quollnet/100086014988886/',
    'https://www.instagram.com/quollnet/',
    'https://twitter.com/quollnet',
    'https://www.linkedin.com/in/quollnet/',
    'https://www.youtube.com/@quollnet',
)


@dataclass(frozen=True)
class PublicPage:
    template_name: str
    destination: str
    canonical_path: str
    title: str
    description: str
    schema_type: str = 'WebPage'
    indexable: bool = True

    @property
    def canonical_url(self) -> str:
        return f'{SITE_ORIGIN}{self.canonical_path}'


PAGES: tuple[PublicPage, ...] = (
    PublicPage(
        'index.html', 'index.html', '/',
        'Construction Cash-Flow Simulation & Forecasting | CashflowPot',
        'Simulate construction project cash flow from execution timing, contract terms and forecasting assumptions for tendering, financing, lender review, budgeting and project reforecasting.',
    ),
    PublicPage(
        'how-it-works.html', 'how-it-works/index.html', '/how-it-works/',
        'How CashflowPot Works | Construction Cash-Flow Forecasting',
        'See how CashflowPot combines execution timing, contract terms and assumptions to simulate construction project inflow, outflow, working capital and funding requirements.',
    ),
    PublicPage(
        'methodology.html', 'methodology/index.html', '/methodology/',
        'CashflowPot Methodology | Construction Cash-Flow Model',
        'Understand how CashflowPot separates execution, contract terms and forecasting assumptions to calculate project inflow, outflow, net cash and funding requirements.',
    ),
    PublicPage(
        'about.html', 'about/index.html', '/about/',
        'About CashflowPot | Construction Cash-Flow Simulation',
        'CashflowPot is a focused construction cash-flow simulation and forecasting product for tendering, financing, lender review, portfolio capacity and project reforecasting.',
        schema_type='AboutPage',
    ),
    PublicPage(
        'contact.html', 'contact/index.html', '/contact/',
        'Contact CashflowPot | Quollnet',
        'Contact the Quollnet team for CashflowPot product questions, feedback and support.',
        schema_type='ContactPage',
    ),
    PublicPage(
        'privacy.html', 'privacy/index.html', '/privacy/',
        'Privacy Notice | CashflowPot',
        'Privacy information for CashflowPot, a Quollnet product operated by Quoll Unipessoal LDA.',
    ),
    PublicPage(
        'terms.html', 'terms/index.html', '/terms/',
        'Terms of Use | CashflowPot',
        'Terms of use for CashflowPot, a Quollnet product operated by Quoll Unipessoal LDA.',
    ),
    PublicPage(
        '404.html', '404.html', '/404.html',
        'Page not found | CashflowPot',
        'The page you’re looking for doesn’t exist or may have moved.',
        indexable=False,
    ),
)


def _structured_data_for(page: PublicPage) -> Optional[Dict[str, Any]]:
    if not page.indexable:
        return None

    if page.canonical_path == '/':
        return {
            '@context': 'https://schema.org',
            '@graph': [
                {
                    '@type': 'Organization',
                    '@id': ORGANIZATION_ID,
                    'name': 'Quollnet',
                    'legalName': 'Quoll Unipessoal LDA',
                    'url': 'https://www.quollnet.com',
                    'sameAs': list(QUOLLNET_SOCIAL_URLS),
                },
                {
                    '@type': 'WebSite',
                    '@id': WEBSITE_ID,
                    'name': 'CashflowPot',
                    'url': f'{SITE_ORIGIN}/',
                    'publisher': {'@id': ORGANIZATION_ID},
                },
                {
                    '@type': 'SoftwareApplication',
                    '@id': SOFTWARE_ID,
                    'name': 'CashflowPot',
                    'url': f'{SITE_ORIGIN}/app/',
                    'applicationCategory': 'BusinessApplication',
                    'operatingSystem': 'Web',
                    'description': (
                        'Construction cash-flow simulation and forecasting for '
                        'project, commercial and finance decisions.'
                    ),
                    'featureList': [
                        'Scenario forecasting',
                        'Activity-based outflow forecasting',
                        'Independent contract curve inflow',
                        'Activity-linked inflow',
                        'Cash position and working capital analysis',
                        'Excel export',
                    ],
                    'publisher': {'@id': ORGANIZATION_ID},
                    'isPartOf': {'@id': WEBSITE_ID},
                },
            ],
        }

    breadcrumb_id = f'{page.canonical_url}#breadcrumb'
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': page.schema_type,
                '@id': f'{page.canonical_url}#webpage',
                'url': page.canonical_url,
                'name': page.title,
                'description': page.description,
                'isPartOf': {'@id': WEBSITE_ID},
                'publisher': {'@id': ORGANIZATION_ID},
                'breadcrumb': {'@id': breadcrumb_id},
            },
            {
                '@type': 'BreadcrumbList',
                '@id': breadcrumb_id,
                'itemListElement': [
                    {
                        '@type': 'ListItem',
                        'position': 1,
                        'name': 'CashflowPot',
                        'item': f'{SITE_ORIGIN}/',
                    },
                    {
                        '@type': 'ListItem',
                        'position': 2,
                        'name': page.title,
                        'item': page.canonical_url,
                    },
                ],
            },
        ],
    }


def _render_robots_txt() -> str:
    return (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /api/\n'
        '\n'
        'User-agent: OAI-SearchBot\n'
        'Allow: /\n'
        'Disallow: /api/\n'
        '\n'
        f'Sitemap: {SITE_ORIGIN}/sitemap.xml\n'
    )


def _render_sitemap_xml() -> str:
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    urls = ''.join(
        f'<url><loc>{page.canonical_url}</loc></url>'
        for page in PAGES
        if page.indexable
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{namespace}">{urls}</urlset>\n'
    )


def _render_llms_txt() -> str:
    return (
        '# CashflowPot\n\n'
        'CashflowPot is a construction cash-flow simulation and forecasting product for '
        'project, commercial and finance decisions. It turns execution timing, contract '
        'terms and forecasting assumptions into expected inflow, outflow, cash position '
        'and working-capital/funding exposure.\n\n'
        '## Canonical public pages\n'
        f'- Home: {SITE_ORIGIN}/\n'
        f'- How it works: {SITE_ORIGIN}/how-it-works/\n'
        f'- Methodology: {SITE_ORIGIN}/methodology/\n'
        f'- About: {SITE_ORIGIN}/about/\n\n'
        '## Application and publisher\n'
        f'- Application: {SITE_ORIGIN}/app/\n'
        '- CashflowPot is part of the Quollnet ecosystem for engineering and construction.\n'
        '- Quollnet listing: https://quollnet.com/apps/cashflowpot\n'
    )


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(('html', 'xml')),
    )


def build_site(output_dir: Optional[Path] = None) -> Path:
    output = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(STATIC_DIR, output / 'assets')

    environment = _environment()
    for page in PAGES:
        target = output / page.destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            environment.get_template(page.template_name).render(
                page=page,
                social_image_url=SOCIAL_IMAGE_URL,
                structured_data=_structured_data_for(page),
            ),
            encoding='utf-8',
        )

    (output / 'robots.txt').write_text(_render_robots_txt(), encoding='utf-8')
    (output / 'sitemap.xml').write_text(_render_sitemap_xml(), encoding='utf-8')
    (output / 'llms.txt').write_text(_render_llms_txt(), encoding='utf-8')
    return output


def _managed_publish_entries() -> tuple[str, ...]:
    entries = {'assets', *ROOT_DISCOVERY_FILES}
    entries.update(Path(page.destination).parts[0] for page in PAGES)
    return tuple(sorted(entries))


def publish_site(build_dir: Path, web_root: Optional[Path] = None) -> Path:
    source_root = Path(build_dir)
    target_root = Path(web_root) if web_root is not None else DEFAULT_WEB_ROOT
    if not target_root.is_dir():
        raise FileNotFoundError(
            f'CashflowPot web root does not exist: {target_root}. '
            'Use -l/--local when building outside the production server.',
        )
    entries = _managed_publish_entries()
    missing = [entry for entry in entries if not (source_root / entry).exists()]
    if missing:
        raise FileNotFoundError(f'Built site is incomplete; missing: {", ".join(missing)}')
    for entry in entries:
        source = source_root / entry
        target = target_root / entry
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return target_root


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Build and publish the static CashflowPot public website.')
    parser.add_argument('-l', '--local', action='store_true', help='Build locally only; do not publish to the production web root.')
    parser.add_argument('--output', type=Path, help='Build output directory. Defaults to site/dist/.')
    args = parser.parse_args(argv)
    output = build_site(args.output)
    if args.local:
        print(f'Built CashflowPot static site locally at {output}')
        return 0
    web_root = publish_site(output)
    print(f'Built CashflowPot static site at {output} and published it to {web_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
