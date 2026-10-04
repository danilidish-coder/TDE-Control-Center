from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def test_home_dashboard_is_completely_removed_from_source():
    root = Path(__file__).resolve().parents[1]
    main = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert '("ΑΡΧΙΚΗ ΣΕΛΙΔΑ", "home")' not in main
    assert 'self.pages["home"]' not in main
    assert "def _home_page(self):" not in main
    assert "class DashboardCard" not in main
    assert '"home":"skin_home.svg"' not in main


def test_application_opens_on_fines_and_shift_controls_stay_visible():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        win.show()
        app.processEvents()
        assert "home" not in win.nav_buttons
        assert "home" not in win.pages
        assert win.stack.currentWidget() is win.pages["fines"]
        assert win.nav_buttons["fines"].isChecked()

        shift_widgets = (win.shift_status, win.shift_detail, win.start_btn, win.close_btn)
        assert all(w.isVisible() for w in shift_widgets)

        win.show_page("refusals")
        app.processEvents()
        assert all(w.isVisible() for w in shift_widgets)

        win.show_page("periodics")
        app.processEvents()
        assert all(w.isVisible() for w in shift_widgets)

        win.show_reports("FINES")
        app.processEvents()
        assert all(w.isVisible() for w in shift_widgets)
    finally:
        win.close()
