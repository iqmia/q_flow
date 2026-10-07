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


class HomepageHeroTest(TestCase):
    def test_homepage_uses_approved_hero_image_only_on_home(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            home = (output / 'index.html').read_text(encoding='utf-8')
            self.assertIn('src="/assets/images/home-hero.webp"', home)
            self.assertIn(
                'alt="Engineer and finance professional reviewing a construction cash-flow forecast"',
                home,
            )
            self.assertIn('fetchpriority="high"', home)
            for relative_path in (
                'how-it-works/index.html', 'methodology/index.html', 'about/index.html',
                'contact/index.html', 'privacy/index.html', 'terms/index.html',
            ):
                html = (output / relative_path).read_text(encoding='utf-8')
                self.assertNotIn('home-hero.webp', html)
