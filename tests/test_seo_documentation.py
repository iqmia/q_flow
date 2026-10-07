from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SeoDocumentationTest(TestCase):
    def test_authoritative_docs_describe_search_discovery_contract(self):
        deployment = (ROOT / 'documentation' / 'deployment.md').read_text(encoding='utf-8')
        technical = (ROOT / 'documentation' / 'technical.md').read_text(encoding='utf-8')
        ui = (ROOT / 'documentation' / 'ui-ux.md').read_text(encoding='utf-8')
        combined = '\n'.join((deployment, technical, ui))

        for token in ('robots.txt', 'sitemap.xml', 'llms.txt', 'cashflowpot-og.webp'):
            self.assertIn(token, combined)
        self.assertIn('/app/', combined)
        self.assertIn('crawlable', combined.casefold())
        self.assertIn('non-indexable', combined.casefold())
        self.assertIn('/api/', combined)
        self.assertIn('not a discovery surface', combined.casefold())
