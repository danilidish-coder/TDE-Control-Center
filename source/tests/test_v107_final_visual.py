from architecture_support import read_application_source
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from app.core.paths import resource_path
from app.ui.main_window import _metallic_emblem_image


def test_final_header_wordart_contract():
    root = Path(__file__).resolve().parents[1]
    main = read_application_source(root)
    theme = (root / "app/ui/theme.py").read_text(encoding="utf-8")
    assert "class FloatingHeaderLabel" in main
    assert "QLinearGradient" in main
    assert "QPainterPath" in main
    assert "Visible grey extrusion" in main
    assert "project above the panel" in main
    assert "_metallic_emblem_image" in main
    assert "ΕΚΔΟΣΗ 1.0.12" in main
    assert "font-weight: 900" in theme
    assert "background: transparent" in theme


def test_official_emblem_is_recoloured_without_white_backing():
    source = QImage(str(resource_path("police_emblem_official.png")))
    assert not source.isNull()
    metallic = _metallic_emblem_image(resource_path("police_emblem_official.png"))
    assert not metallic.isNull()
    assert metallic.hasAlphaChannel()
    assert metallic.pixelColor(0, 0).alpha() == 0
    max_luma = 0.0
    visible = 0
    for y in range(metallic.height()):
        for x in range(metallic.width()):
            c = metallic.pixelColor(x, y)
            if c.alpha() > 20:
                visible += 1
                max_luma = max(max_luma, (c.red() + c.green() + c.blue()) / 3)
    assert visible > 0
    assert max_luma <= 205


def test_refusal_layout_remains_locked():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app/features/refusals/page.py").read_text(encoding="utf-8")
    assert text.count("ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΒΑΣ") == 1
    assert text.count("ΑΡΧΕΙΟ ΒΑΣ") == 1
