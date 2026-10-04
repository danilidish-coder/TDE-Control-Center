from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from app.core.db import Database
from app.docgen.fines_report import FineEntry
from app.services.fines import FineService
from app.services.refusals import RefusalService
from app.ui.fines_page import FinesPage
from app.ui.refusals_page import RefusalsPage


def _seed(db: Database) -> FineService:
    db.start_shift("TEST OFFICER", datetime(2026, 10, 3, 10, 0))
    service = FineService(db)
    service.add_fine("IMPOSITION", FineEntry(
        date="03/10/2026", surname="DANIELIDIS", name="IRAKLIS", birth_date="08/08/1971",
        nationality="ΕΛΛΗΝΙΚΗ", passport="AB123456", measure="ΜΕΤΡΟ 42", amount=600,
        responsible="COLLECTOR ONE", imposition_protocol="P-1",
    ))
    service.add_fine("IMPOSITION", FineEntry(
        date="03/10/2026", surname="DANIELIDIS", name="CHRISTOS", birth_date="01/01/2000",
        nationality="ΕΛΛΗΝΙΚΗ", passport="XY999999", measure="ΜΕΤΡΟ 99", amount=1200,
        responsible="COLLECTOR TWO", imposition_protocol="P-2",
    ))
    return service


def test_database_autocomplete_returns_distinct_history(tmp_path):
    db = Database(tmp_path / "autocomplete.sqlite3")
    _seed(db)
    assert db.autocomplete_values("surname").count("DANIELIDIS") == 1
    assert {"IRAKLIS", "CHRISTOS"}.issubset(set(db.autocomplete_values("given_name")))
    assert "AB123456" in db.autocomplete_values("passport")
    assert "ΕΛΛΗΝΙΚΗ" in db.autocomplete_values("nationality")
    assert db.autocomplete_values("unknown_field") == []


def test_fines_fields_have_excel_like_suggestions_and_no_person_search_button(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "fines.sqlite3")
    service = _seed(db)
    page = FinesPage(service)
    try:
        assert page.surname.completer() is not None
        assert "DANIELIDIS" in page.surname.completer().model().stringList()
        assert "AB123456" in page.passport.completer().model().stringList()
        assert "ΕΛΛΗΝΙΚΗ" in page.nationality.completer().model().stringList()
        assert all(b.text() != "ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ" for b in page.findChildren(QPushButton))
    finally:
        page.close()


def test_refusals_identity_fields_use_same_history_and_no_person_search_button(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "refusals.sqlite3")
    _seed(db)
    page = RefusalsPage(RefusalService(db))
    try:
        assert page.f["surname"].completer() is not None
        assert "DANIELIDIS" in page.f["surname"].completer().model().stringList()
        assert page.f["name"].completer() is not None
        assert "IRAKLIS" in page.f["name"].completer().model().stringList()
        assert "AB123456" in page.f["passport"].completer().model().stringList()
        assert all(b.text() != "ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ" for b in page.findChildren(QPushButton))
    finally:
        page.close()
