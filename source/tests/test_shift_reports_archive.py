import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.core.db import Database
from app.services.daily_activity import DailyActivityService
from app.services.fines import FineService
from app.services.refusals import RefusalService
from app.ui.shift_reports import ShiftReportsPage


def test_thematic_report_archive_page_remains_available(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "test.sqlite3")
    sid = db.start_shift(
        "ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ",
        started_at=datetime(2026, 10, 1, 10, 0),
        officer_agms="12345",
        officer_rank_short="ΑΝΘ/ΜΟΣ",
        officer_rank_full="ΑΝΘ/ΜΟΣ",
    )
    assert sid > 0
    db.close_shift(datetime(2026, 10, 2, 10, 0))
    page = ShiftReportsPage(db, FineService(db), RefusalService(db), DailyActivityService(db))
    page.set_report_type("DAILY")
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ"
    assert "ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ" in page.table.item(0, 2).text()
    page.close()


def test_general_reports_entry_is_removed_but_thematic_buttons_keep_filtered_route():
    root = Path(__file__).resolve().parents[1]
    main = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    fines = (root / "app/ui/fines_page.py").read_text(encoding="utf-8")
    refusals = (root / "app/ui/refusals_page.py").read_text(encoding="utf-8")
    daily = (root / "app/ui/daily_activity.py").read_text(encoding="utf-8")

    assert '("ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ", "reports")' not in main
    assert 'self.pages["reports"] = ShiftReportsPage' in main
    assert "mw.show_reports('FINES')" in fines
    assert "mw.show_reports('VAS')" in refusals
    assert "mw.show_reports('DAILY')" in daily
