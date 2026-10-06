from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


SITE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SITE_DIR / 'templates'
STATIC_DIR = SITE_DIR / 'static'
DEFAULT_OUTPUT_DIR = SITE_DIR / 'dist'

# Public pages are added here one by one after review.
PAGES: tuple[tuple[str, str], ...] = (
    ('index.html', 'index.html'),
    ('how-it-works.html', 'how-it-works/index.html'),
    ('404.html', '404.html'),
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
    for template_name, destination in PAGES:
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            environment.get_template(template_name).render(),
            encoding='utf-8',
        )

    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Build the static CashflowPot public website.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory. Defaults to site/dist/.',
    )
    args = parser.parse_args()

    output = build_site(args.output)
    print(f'Built CashflowPot static site at {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
