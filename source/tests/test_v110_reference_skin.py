from architecture_support import read_application_source, assert_current_version_label
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def test_v110_reference_skin_assets_and_shell_without_home_dashboard():
    root = Path(__file__).resolve().parents[1]
    for name in ("skin_fines.svg","skin_refusals.svg","skin_periodics.svg","skin_people.svg","skin_reports.svg","skin_refresh.svg","skin_greece.svg"):
        assert (root / "resources" / name).exists()
    main = read_application_source(root)
    assert "GreeceWatermark" in main
    assert "b.setIcon(QIcon" in main
    assert_current_version_label(root)
    assert "class DashboardCard" not in main
    assert '("ΑΡΧΙΚΗ ΣΕΛΙΔΑ", "home")' not in main


def test_v110_direct_navigation_replaces_home_cards():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        assert "home" not in win.pages
        assert "home" not in win.nav_buttons
        assert win.stack.currentWidget() is win.pages["fines"]
        win.show_page("refusals")
        assert win.stack.currentWidget() is win.pages["refusals"]
        win.show_page("periodics")
        assert win.stack.currentWidget() is win.pages["periodics"]
    finally:
        win.close()
