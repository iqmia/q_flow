from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape


SITE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SITE_DIR / 'templates'
STATIC_DIR = SITE_DIR / 'static'
DEFAULT_OUTPUT_DIR = SITE_DIR / 'dist'
DEFAULT_WEB_ROOT = Path.home() / 'www.cashflowpot.com'

# Public pages are added here one by one after review.
PAGES: tuple[tuple[str, str], ...] = (
    ('index.html', 'index.html'),
    ('how-it-works.html', 'how-it-works/index.html'),
    ('methodology.html', 'methodology/index.html'),
    ('about.html', 'about/index.html'),
    ('contact.html', 'contact/index.html'),
    ('privacy.html', 'privacy/index.html'),
    ('terms.html', 'terms/index.html'),
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


def _managed_publish_entries() -> tuple[str, ...]:
    entries = {'assets'}
    entries.update(Path(destination).parts[0] for _, destination in PAGES)
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
        raise FileNotFoundError(
            f'Built site is incomplete; missing: {", ".join(missing)}',
        )

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
    parser = argparse.ArgumentParser(
        description='Build and publish the static CashflowPot public website.',
    )
    parser.add_argument(
        '-l',
        '--local',
        action='store_true',
        help='Build locally only; do not publish to the production web root.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Build output directory. Defaults to site/dist/.',
    )
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
