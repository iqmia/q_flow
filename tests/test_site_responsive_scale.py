from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "site" / "static" / "css" / "responsive-scale.css"
BASE = ROOT / "site" / "templates" / "base.html"
HOME = ROOT / "site" / "templates" / "index.html"


def test_shared_template_loads_responsive_scale_css():
    assert '/assets/css/responsive-scale.css' in BASE.read_text(encoding='utf-8')


def test_homepage_uses_split_section_hero_layout():
    text = HOME.read_text(encoding='utf-8')
    assert '<section class="hero">' in text
    assert 'class="site-shell split-section"' in text


def test_responsive_scale_targets_real_homepage_hero_and_caps_heading():
    text = CSS.read_text(encoding='utf-8')
    assert '.hero .split-section' in text
    assert 'grid-template-columns: minmax(0, 1.08fr) minmax(420px, 0.92fr)' in text
    assert '.hero h1' in text
    assert 'font-size: clamp(2.6rem, 3.35vw, 3.35rem)' in text
    assert 'padding-block: clamp(42px, 5vw, 64px)' in text


def test_responsive_scale_keeps_tablet_and_mobile_compact():
    text = CSS.read_text(encoding='utf-8')
    assert '@media (max-width: 900px)' in text
    assert '@media (max-width: 640px)' in text
    assert 'font-size: clamp(2.15rem, 9vw, 2.55rem)' in text
