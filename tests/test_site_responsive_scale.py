from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "site" / "static" / "css" / "responsive-scale.css"
CONTENT_CSS = ROOT / "site" / "static" / "css" / "content-pages.css"
BASE = ROOT / "site" / "templates" / "base.html"
HOME = ROOT / "site" / "templates" / "index.html"


def test_shared_template_loads_responsive_scale_css():
    text = BASE.read_text(encoding='utf-8')
    assert '/assets/css/content-pages.css' in text
    assert '/assets/css/responsive-scale.css' in text


def test_homepage_uses_refreshed_split_section_hero_layout():
    text = HOME.read_text(encoding='utf-8')
    assert '<section class="hero hero--home">' in text
    assert 'class="site-shell split-section"' in text


def test_homepage_specific_scale_outranks_later_generic_hero_rules():
    base = BASE.read_text(encoding='utf-8')
    text = CONTENT_CSS.read_text(encoding='utf-8')

    assert base.index('/assets/css/content-pages.css') < base.index('/assets/css/responsive-scale.css')
    assert '.hero.hero--home {' in text
    assert '.hero.hero--home .split-section' in text
    assert 'grid-template-columns: minmax(0, 0.72fr) minmax(0, 1fr)' in text
    assert '.hero.hero--home h1' in text
    assert 'font-size: clamp(2.6rem, 4vw, 3.6rem)' in text
    assert '.hero.hero--home .hero__image' in text
    assert 'aspect-ratio: 4 / 3' in text
    assert text.count('.hero.hero--home .split-section') >= 2
    assert text.count('.hero.hero--home h1') >= 2


def test_responsive_scale_targets_shared_heroes_and_caps_heading():
    text = CSS.read_text(encoding='utf-8')
    assert '.hero .split-section' in text
    assert 'grid-template-columns: minmax(0, 1.08fr) minmax(420px, 0.92fr)' in text
    assert '.hero h1' in text
    assert 'font-size: clamp(2.6rem, 3.35vw, 3.35rem)' in text
    assert 'padding-block: clamp(42px, 5vw, 64px)' in text


def test_responsive_scale_keeps_tablet_and_mobile_compact():
    text = CSS.read_text(encoding='utf-8')
    content = CONTENT_CSS.read_text(encoding='utf-8')
    assert '@media (max-width: 900px)' in text
    assert '@media (max-width: 900px)' in content
    assert '@media (max-width: 640px)' in text
    assert 'font-size: clamp(2.15rem, 9vw, 2.55rem)' in text
    assert '.hero.hero--home .split-section' in content
    assert 'grid-template-columns: 1fr' in content