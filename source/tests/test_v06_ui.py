import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea, QTabWidget

from app.ui.dialogs import StartShiftDialog
from app.ui.main_window import MainWindow


def test_v06_ui_interaction_and_stress():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()

    fines = win.pages["fines"]
    assert not fines.collection_method.isEnabled()
    assert not fines.collection_protocol.isEnabled()
    assert fines.responsible.isEnabled()

    for i in range(800):
        payment = bool(i % 2)
        fines.kind.setCurrentIndex(1 if payment else 0)
        assert fines.collection_method.isEnabled() is payment
        assert fines.collection_protocol.isEnabled() is payment
        assert fines.responsible.isEnabled()
        fines.responsible.setText(f"TEST OFFICER {i}")
        assert fines.responsible.text() == f"TEST OFFICER {i}"
        if payment:
            fines.collection_method.setCurrentText("TEST")
            fines.collection_protocol.setText(str(i))
            assert fines.collection_protocol.text() == str(i)

    refusals = win.pages["refusals"]
    assert refusals.f["reason"].count() > 0
    assert refusals.f["language"].count() > 1
    for i in range(600):
        refusals.f["reason"].setCurrentIndex(i % refusals.f["reason"].count())
        refusals.f["language"].setCurrentIndex(i % refusals.f["language"].count())

    people = win.pages["people"]
    button_texts = {b.text() for b in people.findChildren(QPushButton)}
    assert "ΧΡΗΣΗ ΣΤΑ ΠΡΟΣΤΙΜΑ" not in button_texts
    assert "ΧΡΗΣΗ ΣΤΙΣ ΑΡΝΗΣΕΙΣ" not in button_texts

    daily = win.pages["daily"]
    tabs = daily.findChildren(QTabWidget)
    assert len(tabs) == 1 and tabs[0].count() == 3
    assert [tabs[0].tabText(i) for i in range(3)] == ["ΠΡΟΣΤΙΜΑ", "ΑΡΝΗΣΕΙΣ", "ΛΟΙΠΕΣ ΠΡΑΞΕΙΣ"]
    other_page=tabs[0].widget(2)
    other_scrolls=[x for x in other_page.findChildren(QScrollArea) if x.objectName()=="OtherActsScroll"]
    assert len(other_scrolls)==1
    assert other_scrolls[0].widgetResizable()
    assert daily.auto_edit_inputs
    refusal_fields = win.pages["refusals"].f
    for key in ("surname","name","birth_place","nationality","residence","passport","passport_issuer","origin_country"):
        assert refusal_fields[key].minimumWidth() >= 160
        assert refusal_fields[key].maxLength() >= 1000
        sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        refusal_fields[key].setText(sample)
        assert refusal_fields[key].text() == sample
    for key in ("birth_place","nationality","residence","passport_issuer","origin_country"):
        assert key in refusal_fields
    assert "QComboBox QAbstractItemView" in win.styleSheet()
    assert "qlineargradient" in win.styleSheet()
    assert "ΔΙΕΥΘΥΝΣΗ ΑΣΤΥΝΟΜΙΑΣ ΦΛΩΡΙΝΑΣ" in win.findChild(type(win.clock), "HeaderLine1").text()
    assert "ΤΜΗΜΑ ΔΙΑΒΑΤΗΡΙΑΚΟΥ ΕΛΕΓΧΟΥ ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ" in win.findChild(type(win.clock), "HeaderLine2").text()

    shift_dialog = StartShiftDialog(win)
    assert hasattr(shift_dialog, "rank")
    assert hasattr(shift_dialog, "agms")
    assert hasattr(shift_dialog, "surname")
    assert hasattr(shift_dialog, "name")
    assert shift_dialog.rank.placeholderText() == "ΒΑΘΜΟΣ"
    assert "QDialog" in win.styleSheet()
    shift_dialog.close()

    for _ in range(60):
        win.toggle_theme()

    win.close()
