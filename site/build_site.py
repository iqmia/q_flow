import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SITE_DIR / 'templates'
STATIC_DIR = SITE_DIR / 'static'
DEFAULT_OUTPUT_DIR = SITE_DIR / 'dist'
DEFAULT_WEB_ROOT = Path.home() / 'www.cashflowpot.com'
SITE_ORIGIN = 'https://cashflowpot.com'
SOCIAL_IMAGE_URL = f'{SITE_ORIGIN}/assets/images/cashflowpot-og.webp'


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
            ),
            encoding='utf-8',
        )
    return output


def _managed_publish_entries() -> tuple[str, ...]:
    entries = {'assets'}
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
