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


class LlmsTxtTest(TestCase):
    def test_llms_txt_uses_markdown_links_for_discoverable_resources(self):
        module = _load_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = module.build_site(Path(temp_dir) / 'site-output')
            llms = (output / 'llms.txt').read_text(encoding='utf-8')

        self.assertTrue(llms.startswith('# CashflowPot\n'))
        for link in (
            '[Home](https://cashflowpot.com/)',
            '[How it works](https://cashflowpot.com/how-it-works/)',
            '[Methodology](https://cashflowpot.com/methodology/)',
            '[About](https://cashflowpot.com/about/)',
            '[Contact](https://cashflowpot.com/contact/)',
            '[Privacy](https://cashflowpot.com/privacy/)',
            '[Terms](https://cashflowpot.com/terms/)',
            '[Open CashflowPot](https://cashflowpot.com/app/)',
            '[CashflowPot on Quollnet](https://quollnet.com/apps/cashflowpot)',
        ):
            self.assertIn(link, llms)
