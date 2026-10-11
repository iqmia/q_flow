from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "site" / "static" / "css" / "responsive-scale.css"
BASE = ROOT / "site" / "templates" / "base.html"


def test_shared_template_loads_responsive_scale_css():
    assert '/assets/css/responsive-scale.css' in BASE.read_text(encoding='utf-8')


def test_responsive_scale_caps_desktop_headings_and_tightens_hero():
    text = CSS.read_text(encoding='utf-8')
    assert 'clamp(2.5rem, 3.5vw, 4rem)' in text
    assert 'padding-block: clamp(48px, 6vw, 76px)' in text
    assert 'grid-template-columns: minmax(0, 0.95fr) minmax(420px, 1.05fr)' in text


def test_responsive_scale_keeps_mobile_single_column_and_compact():
    text = CSS.read_text(encoding='utf-8')
    assert '@media (max-width: 900px)' in text
    assert '@media (max-width: 640px)' in text
    assert 'font-size: clamp(2.25rem, 10vw, 2.75rem)' in text
