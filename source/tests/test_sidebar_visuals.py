from architecture_support import read_application_source
from pathlib import Path


def test_sidebar_labels_and_icons_are_applied():
    root = Path(__file__).resolve().parents[1]
    main = read_application_source(root)
    from app.registry import DEFAULT_MODULES, navigation_modules
    modules = {m.key: m for m in DEFAULT_MODULES}
    assert modules["fines"].icon == "skin_nav_fines.svg"
    assert modules["daily"].icon == "skin_nav_daily.svg"
    assert modules["receipts"].icon == "skin_nav_receipts.svg"
    assert modules["receipts"].title == "ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ"
    assert "reports" not in [m.key for m in navigation_modules(DEFAULT_MODULES)]
    assert 'QSize(40,40) if page == "fines" else QSize(35,35)' in main



def test_sidebar_svg_assets_are_packaged():
    root = Path(__file__).resolve().parents[1]
    names = [
        "skin_nav_fines.svg",
        "skin_nav_receipts.svg",
        "skin_nav_daily.svg",
        "skin_nav_reports.svg",
    ]
    spec = (root / "TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    for name in names:
        svg = root / "resources" / name
        assert svg.exists()
        text = svg.read_text(encoding="utf-8")
        assert "<svg" in text and "</svg>" in text
        assert name in spec
