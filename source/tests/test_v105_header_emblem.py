from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from app.core.paths import resource_path


def test_police_emblem_resource_is_valid_image():
    path = resource_path("police_emblem.jpeg")
    assert path.exists()
    pixmap = QPixmap(str(path))
    assert not pixmap.isNull()


def test_main_header_uses_existing_police_emblem():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert 'resource_path("police_emblem_user.png")' in text
    assert 'setObjectName("PoliceEmblem")' in text
    assert "Qt.KeepAspectRatio" in text
    assert "Qt.SmoothTransformation" in text


def test_pyinstaller_already_packages_police_emblem():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    assert "police_emblem.jpeg" in spec
    assert "police_emblem.ico" in spec
