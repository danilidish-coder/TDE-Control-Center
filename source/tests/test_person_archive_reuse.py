import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.core.db import Database
from app.ui.person_archive import PersonArchivePage


def test_person_archive_buttons_emit_selected_profile(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "people.sqlite3")
    person_id = db.get_or_create_person("DOE", "JOHN", "01/02/1990")
    db.add_action(person_id, "REFUSAL", passport_no="AB123456")

    page = PersonArchivePage(db)
    captured_fines = []
    captured_refusals = []
    page.useInFines.connect(captured_fines.append)
    page.useInRefusals.connect(captured_refusals.append)

    assert not page.use_fines_btn.isEnabled()
    assert not page.use_refusals_btn.isEnabled()

    page.surname.setText("DOE")
    page.given.setText("JOHN")
    page.birth.setText("01/02/1990")
    page.run_search()
    assert page.people_table.rowCount() == 1

    page.people_table.selectRow(0)
    app.processEvents()
    assert page.use_fines_btn.isEnabled()
    assert page.use_refusals_btn.isEnabled()

    page.use_fines_btn.click()
    page.use_refusals_btn.click()

    assert captured_fines and captured_refusals
    for payload in (captured_fines[-1], captured_refusals[-1]):
        assert payload["surname"] == "DOE"
        assert payload["given_name"] == "JOHN"
        assert payload["birth_date"]
        assert payload["passport_no"] == "AB123456"

    page.close()


def test_main_window_wires_person_archive_to_fines_and_refusals():
    root = Path(__file__).resolve().parents[1]
    main = (root / "app/ui/main_window.py").read_text(encoding="utf-8")
    fines = (root / "app/ui/fines_page.py").read_text(encoding="utf-8")
    refusals = (root / "app/ui/refusals_page.py").read_text(encoding="utf-8")

    assert 'self.pages["people"].useInFines.connect' in main
    assert 'self.pages["people"].useInRefusals.connect' in main
    assert 'def apply_person' in fines
    assert "self.surname.setText(x.get(" in fines
    assert "self.passport.setText(x.get(" in fines
    assert 'def apply_person' in refusals
    assert "self.f[\"surname\"].setText(x.get(" in refusals or "self.f['surname'].setText(x.get(" in refusals
    assert "self.f[\"passport\"].setText(x.get(" in refusals or "self.f['passport'].setText(x.get(" in refusals
