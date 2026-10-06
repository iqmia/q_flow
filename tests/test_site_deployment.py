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


class SiteDeploymentTest(TestCase):
    def test_publish_replaces_only_site_owned_paths(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build = module.build_site(root / 'dist')
            web_root = root / 'www.cashflowpot.com'
            web_root.mkdir()

            for protected in ('app', 'api'):
                directory = web_root / protected
                directory.mkdir()
                (directory / 'keep.txt').write_text('keep', encoding='utf-8')

            (web_root / 'unrelated.txt').write_text('keep', encoding='utf-8')
            (web_root / 'index.html').write_text('old home', encoding='utf-8')
            (web_root / 'about').mkdir()
            (web_root / 'about' / 'stale.txt').write_text('stale', encoding='utf-8')

            published = module.publish_site(build, web_root)

            self.assertEqual(published, web_root)
            self.assertNotEqual((web_root / 'index.html').read_text(encoding='utf-8'), 'old home')
            self.assertTrue((web_root / 'about' / 'index.html').is_file())
            self.assertFalse((web_root / 'about' / 'stale.txt').exists())
            self.assertEqual((web_root / 'app' / 'keep.txt').read_text(encoding='utf-8'), 'keep')
            self.assertEqual((web_root / 'api' / 'keep.txt').read_text(encoding='utf-8'), 'keep')
            self.assertEqual((web_root / 'unrelated.txt').read_text(encoding='utf-8'), 'keep')

    def test_publish_requires_existing_web_root(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build = module.build_site(root / 'dist')

            with self.assertRaises(FileNotFoundError):
                module.publish_site(build, root / 'missing-web-root')

    def test_default_mode_builds_and_publishes_to_default_web_root(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.DEFAULT_OUTPUT_DIR = root / 'dist'
            module.DEFAULT_WEB_ROOT = root / 'www.cashflowpot.com'
            module.DEFAULT_WEB_ROOT.mkdir()

            self.assertEqual(module.main([]), 0)
            self.assertTrue((root / 'dist' / 'index.html').is_file())
            self.assertTrue((module.DEFAULT_WEB_ROOT / 'index.html').is_file())

    def test_local_flag_builds_without_touching_server_web_root(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.DEFAULT_OUTPUT_DIR = root / 'dist'
            module.DEFAULT_WEB_ROOT = root / 'missing-web-root'

            self.assertEqual(module.main(['-l']), 0)
            self.assertTrue((root / 'dist' / 'index.html').is_file())
            self.assertFalse(module.DEFAULT_WEB_ROOT.exists())
