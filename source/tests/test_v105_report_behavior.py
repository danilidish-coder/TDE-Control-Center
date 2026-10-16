from datetime import datetime
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.core.db import Database
from app.services.fines import FineService
from app.services.refusals import RefusalService
from app.services.daily_activity import DailyActivityService
from app.ui.shift_reports import ShiftReportsPage


def test_current_or_last_shift_prefers_open_then_latest_closed(tmp_path: Path):
    db=Database(tmp_path/"x.sqlite3")
    first=db.start_shift("ONE", datetime(2026,10,1,10,0))
    db.close_shift(datetime(2026,10,2,10,0))
    assert int(db.get_current_or_last_shift()["id"])==first
    second=db.start_shift("TWO", datetime(2026,10,2,10,1))
    assert int(db.get_current_or_last_shift()["id"])==second


def test_report_archive_locks_scope_by_module(tmp_path: Path):
    app=QApplication.instance() or QApplication([])
    db=Database(tmp_path/"x.sqlite3")
    page=ShiftReportsPage(db,FineService(db),RefusalService(db),DailyActivityService(db))
    page.set_report_type("FINES")
    assert page.report_type.isHidden()
    assert page.report_type.currentData()=="FINES"
    assert page.title.text()=="ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ"
    page.set_report_type("VAS")
    assert page.report_type.isHidden()
    assert page.report_type.currentData()=="VAS"
    assert page.title.text()=="ΑΡΧΕΙΟ ΒΑΣ"
    page.set_report_type("")
    assert not page.report_type.isHidden()
    page.close()


def test_refusal_archive_is_all_shifts_and_has_individual_and_shift_list_actions():
    root=Path(__file__).resolve().parents[1]
    service=(root/"app/features/refusals/service.py").read_text(encoding="utf-8")
    ui=(root/"app/features/refusals/archive.py").read_text(encoding="utf-8")
    assert "JOIN shifts s ON s.id=r.shift_id" in service
    assert "WHERE 1=1" in service
    assert "ΑΝΟΙΓΜΑ ΕΠΙΛΕΓΜΕΝΗΣ ΑΡΝΗΣΗΣ" in ui
    assert "ΑΝΟΙΓΜΑ / ΕΚΤΥΠΩΣΗ ΒΑΣ ΒΑΡΔΙΑΣ" in ui
    assert "generate_vas(int(shift_id),archive=True)" in ui


def test_current_report_buttons_use_current_or_last_shift():
    root=Path(__file__).resolve().parents[1]
    fines=(root/"app/features/fines/page.py").read_text(encoding="utf-8")
    refusals=(root/"app/features/refusals/page.py").read_text(encoding="utf-8")
    daily=(root/"app/features/daily_activity/page.py").read_text(encoding="utf-8")
    assert "get_current_or_last_shift" in fines
    assert "get_current_or_last_shift" in refusals
    assert "get_current_or_last_shift" in daily
