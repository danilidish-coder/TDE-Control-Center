import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.core.db import Database
from app.services.protocol_workbook import TestProtocolWorkbookWriter
from app.services.receipts import ReceiptService
from app.ui.receipts_page import ReceiptsPage


def _seed(service):
    return service.add_receipt(
        "ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ", "DOE", "JOHN", "01/01/1990", 600,
        payment_type="e-ΠΑΡΑΒΟΛΟ", protocol_no="123", measure="456", paravolo="789",
    )


def test_receipt_list_survives_shift_and_preview_does_not_close(tmp_path, monkeypatch):
    db = Database(tmp_path / "tde.sqlite3")
    service = ReceiptService(db, writer=TestProtocolWorkbookWriter())
    _seed(service)
    row = service.get_open_list("ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ")
    list_id = int(row["id"])

    db.start_shift("OFFICER")
    db.close_shift(datetime.now())
    assert service.get_list(list_id)["status"] == "OPEN"

    import app.services.receipts as receipts_mod
    monkeypatch.setattr(receipts_mod, "preview_root", lambda: tmp_path / "preview")
    path = service.preview_list(list_id)
    assert path.suffix == ".pdf" and path.exists()
    assert service.get_list(list_id)["status"] == "OPEN"


def test_close_requires_receiver_and_creates_next_open_list(tmp_path, monkeypatch):
    db = Database(tmp_path / "tde.sqlite3")
    service = ReceiptService(db, writer=TestProtocolWorkbookWriter())
    _seed(service)
    import app.services.receipts as receipts_mod
    monkeypatch.setattr(receipts_mod, "archive_root", lambda: tmp_path / "archive")

    out = service.close_list(
        "ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ",
        "ΑΝΘ/ΜΟΣ ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ",
        datetime(2026, 10, 4, 12, 30),
    )
    assert out.suffix == ".pdf" and out.exists()
    row = service.list_summaries("ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ")[0]
    assert row["status"] == "CLOSED"
    assert row["receiver_name"] == "ΑΝΘ/ΜΟΣ ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ"
    workbook = Path(row["archive_path"])
    text = workbook.read_text(encoding="utf-8")
    assert "collector=ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ" in text
    assert "receiver=ΑΝΘ/ΜΟΣ ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ" in text

    _seed(service)
    assert int(service.get_open_list("ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ")["id"]) != int(row["id"])


def test_receipts_page_shows_open_closed_lists_and_handover_actions(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "tde.sqlite3")
    service = ReceiptService(db, writer=TestProtocolWorkbookWriter())
    _seed(service)
    page = ReceiptsPage(service)
    labels = [page.table.horizontalHeaderItem(i).text() for i in range(page.table.columnCount())]
    assert page.table.columnCount() == 8
    assert "ΕΙΣΠΡΑΤΤΩΝ" in labels
    assert "ΠΑΡΑΛΑΒΩΝ" in labels
    assert "ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ" in page.preview_btn.text()
    assert "ΚΛΕΙΣΙΜΟ - ΠΑΡΑΔΟΣΗ" in page.close_btn.text()
    source = (Path(__file__).resolve().parents[1] / "app/features/receipts/page.py").read_text(encoding="utf-8")
    assert "QInputDialog.getText" in source
    assert "Συμπλήρωσε τον Παραλαβόντα" in source
    assert page.table.rowCount() == 1
    page.table.selectRow(0)
    app.processEvents()
    assert page.preview_btn.isEnabled()
    assert page.close_btn.isEnabled()
    page.close()


def test_pdf_preview_helper_is_used_for_final_reports():
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "app/features/fines/page.py",
        root / "app/features/refusals/page.py",
        root / "app/features/fines/archive.py",
        root / "app/features/refusals/archive.py",
        root / "app/features/reports/page.py",
        root / "app/features/daily_activity/service.py",
        root / "app/features/refusals/service.py",
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        if path.name == "page.py" and path.parent.name == "fines" or path.name == "archive.py" and path.parent.name == "fines":
            assert "open_word_document" in text
            assert "open_document_preview" not in text
        else:
            assert "open_document_preview" in text
        if path.parent.name == "reports":
            assert "open_word_document" in text
