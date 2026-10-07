from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / 'site' / 'templates'


class PublicPageRegistryTest(TestCase):
    def test_content_templates_do_not_override_registry_metadata(self):
        for name in (
            'index.html',
            'how-it-works.html',
            'methodology.html',
            'about.html',
            'contact.html',
            'privacy.html',
            'terms.html',
            '404.html',
        ):
            text = (TEMPLATES / name).read_text(encoding='utf-8')
            for block in ('title', 'description', 'canonical_url', 'head_extra'):
                self.assertNotIn('{% block ' + block, text, f'{name}: {block}')
