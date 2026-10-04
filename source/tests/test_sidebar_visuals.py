from pathlib import Path


def test_sidebar_labels_and_icons_are_applied():
    root = Path(__file__).resolve().parents[1]
    main = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert '"fines":"skin_nav_fines.svg"' in main
    assert '"daily":"skin_nav_daily.svg"' in main
    assert '"reports":"skin_nav_reports.svg"' not in main
    assert '"receipts":"skin_nav_receipts.svg"' in main
    assert '("ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ", "receipts")' in main
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
