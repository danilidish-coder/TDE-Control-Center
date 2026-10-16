from architecture_support import read_application_source
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def test_v108_user_emblem_and_no_recolouring_in_header():
    root = Path(__file__).resolve().parents[1]
    main = read_application_source(root)
    spec = (root / "TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    asset = root / "resources/police_emblem_user.png"
    assert asset.exists()
    assert asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert 'QPixmap(str(resource_path("police_emblem_user.png")))' in main
    assert '_metallic_emblem_image(resource_path("police_emblem_official.png"))' not in main
    assert "emblem_shadow.setOffset(2,8)" in main
    assert "police_emblem_user.png" in spec


def test_v108_left_navigation_is_exclusive_and_green():
    root = Path(__file__).resolve().parents[1]
    main = read_application_source(root)
    theme = (root / "app/ui/theme.py").read_text(encoding="utf-8")
    assert "self.nav_buttons = {}" in main
    assert 'b.setProperty("navButton", True)' in main
    assert "b.setCheckable(True)" in main
    assert "b.setAutoExclusive(True)" in main
    assert "self.stack.currentChanged.connect(self._sync_active_nav)" in main
    assert 'QPushButton[navButton="true"]:checked' in theme
    assert "#2ebd70" in theme
    assert "#11683f" in theme


def test_v108_navigation_runtime_state_without_general_reports_button():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        win.show_page("fines")
        assert win.nav_buttons["fines"].isChecked()
        assert not win.nav_buttons["refusals"].isChecked()
        win.show_page("refusals")
        assert win.nav_buttons["refusals"].isChecked()
        assert not win.nav_buttons["fines"].isChecked()
        assert "reports" not in win.nav_buttons
        win.show_reports("FINES")
        assert win.stack.currentWidget() is win.pages["reports"]
    finally:
        win.close()
