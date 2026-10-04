from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.core.db import Database
from app.docgen.refusals import REFUSAL_REASONS, RefusalEntry
from app.services.daily_activity import DailyActivityService as RealDailyActivityService
from app.services.pending import DAILY_ACTIVITY, REFUSALS_VAS
from app.services.refusals import RefusalService


class FakeIndividualEngine:
    def create(self, path, entry):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"{entry.surname}|{entry.name}|{entry.passport}|{entry.reason}|{entry.protocol_prefix}|{entry.protocol_no}",
            encoding="utf-8",
        )


class FakeVasEngine:
    def create(self, path, entries, *args, **kwargs):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(f"{e.surname}|{e.name}|{e.passport}|{e.reason}" for e in entries),
            encoding="utf-8",
        )


class FakeDaily:
    calls = []

    def __init__(self, db):
        self.db = db

    def generate(self, shift_id, archive=False):
        self.calls.append((int(shift_id), bool(archive)))
        return Path(f"daily-{shift_id}.xlsx")


def make_case(tmp_path, monkeypatch):
    preview = tmp_path / "preview"
    archive = tmp_path / "archive"
    preview.mkdir()
    archive.mkdir()
    monkeypatch.setattr("app.services.refusals.preview_root", lambda: preview)
    monkeypatch.setattr("app.services.refusals.archive_root", lambda: archive)
    monkeypatch.setattr("app.services.refusals.DailyActivityService", FakeDaily)
    FakeDaily.calls.clear()
    db = Database(tmp_path / "refusals.sqlite3")
    sid = db.start_shift("TEST OFFICER", datetime(2026, 10, 1, 10, 0))
    service = RefusalService(db)
    service.individual_engine = FakeIndividualEngine()
    service.vas_engine = FakeVasEngine()
    entry = RefusalEntry(
        aa="1", year="2026", protocol_prefix="REF", protocol_no="100",
        date="01-10-2026", time="11:00", sex="M", surname="WRONG", name="PERSON",
        birth_date="01-01-1990", passport="P-1", issue_date="01-01-2025",
        reason=REFUSAL_REASONS[0], language="ΑΛΒΑΝΙΚΑ",
        birth_place="ΑΛΒΑΝΙΑ", nationality="ΑΛΒΑΝΙΚΗ", residence="ΤΙΡΑΝΑ",
        passport_issuer="ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ", origin_country="ΑΛΒΑΝΙΑ (ALBANIA)",
    )
    rid, latest, _, individual = service.add_refusal(entry)
    return db, sid, service, rid, entry, latest, individual, archive


def test_historical_refusal_correction_rewrites_individual_vas_and_daily(tmp_path, monkeypatch):
    db, sid, service, rid, entry, latest, individual, _ = make_case(tmp_path, monkeypatch)
    db.close_shift(datetime(2026, 10, 2, 10, 0))
    vas = service.generate_vas(sid, archive=True)
    assert "WRONG" in vas.read_text(encoding="utf-8")
    db.start_shift("NEXT OFFICER", datetime(2026, 10, 2, 10, 1))

    corrected = replace(entry, surname="CORRECT", passport="P-NEW", protocol_no="101")
    result = service.update_refusal(rid, corrected, expected_entry=entry)

    assert result.failed == []
    assert REFUSALS_VAS in result.completed and DAILY_ACTIVITY in result.completed
    row = service.get_refusal(rid)
    assert row["surname"] == "CORRECT" and row["passport_no"] == "P-NEW"
    assert "CORRECT" in individual.read_text(encoding="utf-8")
    assert "WRONG" not in individual.read_text(encoding="utf-8")
    assert "CORRECT" in vas.read_text(encoding="utf-8")
    assert "CORRECT" in latest.read_text(encoding="utf-8")
    assert (sid, True) in FakeDaily.calls


def test_historical_refusal_delete_removes_individual_stale_vas_and_daily_count(tmp_path, monkeypatch):
    db, sid, service, rid, entry, latest, individual, _ = make_case(tmp_path, monkeypatch)
    db.close_shift(datetime(2026, 10, 2, 10, 0))
    vas = service.generate_vas(sid, archive=True)
    assert individual.exists() and vas.exists() and latest.exists()
    db.start_shift("NEXT OFFICER", datetime(2026, 10, 2, 10, 1))

    result = service.delete_refusal(rid, expected_entry=entry)

    assert result.failed == []
    assert service.get_refusal(rid) is None
    assert not individual.exists()
    assert not vas.exists()
    assert not latest.exists()
    assert (sid, True) in FakeDaily.calls
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM refusals WHERE shift_id=?", (sid,)).fetchone()[0] == 0


def test_refusal_stale_edit_does_not_overwrite_other_station(tmp_path, monkeypatch):
    _, _, service, rid, entry, _, _, _ = make_case(tmp_path, monkeypatch)
    service.update_refusal(rid, replace(entry, passport="CHANGED"))
    try:
        service.update_refusal(rid, replace(entry, surname="SECOND"), expected_entry=entry)
        assert False, "stale correction should have failed"
    except ValueError as exc:
        assert "άλλον σταθμό" in str(exc)
    assert service.get_refusal(rid)["passport_no"] == "CHANGED"


def test_refusal_ui_and_archives_expose_same_correction_actions():
    root = Path(__file__).resolve().parents[1]
    page = (root / "app/ui/refusals_page.py").read_text(encoding="utf-8")
    archive = (root / "app/ui/refusals_archive.py").read_text(encoding="utf-8")
    fines_archive = (root / "app/ui/fines_archive.py").read_text(encoding="utf-8")
    assert "ΑΡΝΗΣΕΙΣ ΒΑΡΔΙΑΣ — ΚΑΤΑΧΩΡΙΣΕΙΣ" in page
    assert "ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ" in page and "ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ" in page
    assert "ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ" in archive and "ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ" in archive
    assert "AdjustToMinimumContentsLengthWithIcon" in page
    assert "setMinimumContentsLength(1)" in page
    assert "QScrollArea" in page and "scroll.setWidgetResizable(True)" in page
    assert "self.table.setMinimumHeight(150)" in page
    assert "visible_rows=max(4,min(len(rows),10))" in page
    assert "self.clear_btn.setMaximumHeight(42)" in page and "self.save_btn.setMaximumHeight(42)" in page
    assert "identity_pairs=[" in page and "identity_grid=QGridLayout()" in page
    assert "national_title=QLabel('ΕΘΝΙΚΟ ΜΕΤΡΟ')" in page
    assert "sis_title=QLabel('SIS')" in page and "sis_grid=QGridLayout()" in page
    assert "ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ" in fines_archive and "ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ" in fines_archive
