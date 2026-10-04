from pathlib import Path

def test_v111_greece_watermark_is_replaced_only_visually():
    root = Path(__file__).resolve().parents[1]
    svg = (root / "resources" / "skin_greece.svg").read_text(encoding="utf-8")
    main = (root / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert '<svg' in svg
    assert 'viewBox="0 0 1828 1704"' in svg
    assert svg.count('<path') >= 2
    assert svg.count('<path') >= 50
    assert 'ΕΚΔΟΣΗ 1.0.12' in main
