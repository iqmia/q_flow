import importlib.util
import json
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "site" / "build_site.py"
BASE_TEMPLATE = REPO_ROOT / "site" / "templates" / "base.html"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "cashflowpot_site_builder",
        BUILD_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PublicManifestTest(TestCase):
    def test_public_manifest_is_built_and_reuses_flutter_icons(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / "site-output")
            manifest_path = output / "assets" / "manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "CashflowPot")
        self.assertEqual(manifest["short_name"], "CashflowPot")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["theme_color"], "#E89A5B")
        self.assertEqual(manifest["background_color"], "#F7F4EF")

        icon_sources = {icon["src"] for icon in manifest["icons"]}
        self.assertEqual(
            icon_sources,
            {
                "/app/icons/Icon-192.png",
                "/app/icons/Icon-512.png",
                "/app/icons/Icon-maskable-192.png",
                "/app/icons/Icon-maskable-512.png",
            },
        )
        self.assertFalse((output / "assets" / "icons").exists())

    def test_shared_head_uses_app_favicon_and_public_manifest(self):
        template = BASE_TEMPLATE.read_text(encoding="utf-8")
        for token in (
            'rel="icon" type="image/png" href="/app/favicon.png"',
            'rel="apple-touch-icon" href="/app/icons/Icon-192.png"',
            'rel="manifest" href="/assets/manifest.json"',
            'name="theme-color" content="#E89A5B"',
        ):
            self.assertIn(token, template)
