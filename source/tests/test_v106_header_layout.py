from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage


def test_v106_header_text_and_version_placement():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert "ΔΙΕΥΘΥΝΣΗ ΑΣΤΥΝΟΜΙΑΣ ΦΛΩΡΙΝΑΣ" in text
    assert "ΤΜΗΜΑ ΔΙΑΒΑΤΗΡΙΑΚΟΥ ΕΛΕΓΧΟΥ ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ" in text
    assert "ΚΕΝΤΡΟ ΕΛΕΓΧΟΥ ΑΞΙΩΜΑΤΙΚΟΥ ΥΠΗΡΕΣΙΑΣ" in text
    assert 'self.version_label = QLabel("ΕΚΔΟΣΗ 1.0.12")' in text
    assert text.index("self.pending_btn") < text.index("self.version_label") < text.index("body.addWidget(side)")
    assert 'ΚΕΝΤΡΟ ΕΛΕΓΧΟΥ · ΕΚΔΟΣΗ 1.0.5' not in text
    assert "_raised_header_label" in text
    assert "QGraphicsDropShadowEffect" in text


def test_official_emblem_has_transparent_background_and_is_packaged():
    root = Path(__file__).resolve().parents[1]
    path = root / "resources/police_emblem_official.png"
    assert path.exists()
    image = QImage(str(path))
    assert not image.isNull()
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    main = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    spec = (root / "TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    assert 'resource_path("police_emblem_user.png")' in main
    assert "police_emblem_user.png" in spec
    assert "emblem_shadow" in main


def test_refusal_bas_buttons_are_beside_other_actions_not_bottom():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app/ui/refusals_page.py").read_text(encoding="utf-8")
    assert text.count("ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΒΑΣ") == 1
    assert text.count("ΑΡΧΕΙΟ ΒΑΣ") == 1
    tools_start = text.index("tools=QHBoxLayout()")
    forms_start = text.index("self.f={}")
    vas_pos = text.index("ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΒΑΣ")
    archive_pos = text.index("ΑΡΧΕΙΟ ΒΑΣ")
    bottom_pos = text.index("ar=QHBoxLayout(); ar.addStretch(1)")
    assert tools_start < vas_pos < forms_start
    assert tools_start < archive_pos < forms_start
    assert bottom_pos > forms_start


def test_header_uses_single_futuristic_font_family():
    root = Path(__file__).resolve().parents[1]
    theme = (root / "app/ui/theme.py").read_text(encoding="utf-8")
    assert "QLabel#HeaderLine1, QLabel#HeaderLine2, QLabel#HeaderLine3" in theme
    assert "Bahnschrift SemiCondensed" in theme
    assert "QLabel#VersionLabel" in theme
