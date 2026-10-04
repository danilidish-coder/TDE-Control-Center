from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from app.core.db import Database
from app.docgen.refusal_languages import LANGUAGES
from app.docgen.refusals import RefusalDocumentEngine, RefusalEntry
from app.services.receipts import ReceiptService
from app.services.protocol_workbook import TestProtocolWorkbookWriter


def test_turkish_refusal_is_available_and_translated(tmp_path: Path):
    assert "ΤΟΥΡΚΙΚΑ" in LANGUAGES
    template = Path(__file__).resolve().parents[1] / "resources" / "Master_Template_Arnisi.docx"
    out = tmp_path / "turkish.docx"
    entry = RefusalEntry(
        aa="1", year="2026", protocol_prefix="6633", protocol_no="61000",
        date="25-09-2026", time="12:30", sex="M", surname="TEST", name="PERSON",
        birth_date="01-01-1990", passport="AA123", issue_date="01-01-2025",
        reason="A-ΕΛΛΕΙΨΗ ΕΓΚΥΡΟΥ ΤΑΞ. ΕΓΓΡΑΦΟΥ", language="ΤΟΥΡΚΙΚΑ",
    )
    RefusalDocumentEngine(template).create(out, entry)
    with ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "SINIRDA GİRİŞİN REDDİ" in xml
    assert "Soyadı" in xml


def test_receipt_list_continues_until_explicit_close(tmp_path: Path, monkeypatch):
    import app.services.receipts as receipts_mod
    archive = tmp_path / "archive"
    monkeypatch.setattr(receipts_mod, "archive_root", lambda: archive)
    db = Database(tmp_path / "db.sqlite3")
    svc = ReceiptService(db, writer=TestProtocolWorkbookWriter())
    svc.add_receipt("ΔΑΝΙΗΛΙΔΗΣ", "A", "ONE", "01/01/1990", 600)
    first = svc.get_open_list("ΔΑΝΙΗΛΙΔΗΣ")
    svc.add_receipt("ΔΑΝΙΗΛΙΔΗΣ", "B", "TWO", "02/02/1991", 1200)
    second = svc.get_open_list("ΔΑΝΙΗΛΙΔΗΣ")
    assert first["id"] == second["id"]
    summaries = svc.list_summaries("ΔΑΝΙΗΛΙΔΗΣ")
    assert len(summaries) == 1 and summaries[0]["receipt_count"] == 2
    svc.close_list("ΔΑΝΙΗΛΙΔΗΣ", datetime(2026,9,25,20,0,0))
    svc.add_receipt("ΔΑΝΙΗΛΙΔΗΣ", "C", "THREE", "03/03/1992", 600)
    third = svc.get_open_list("ΔΑΝΙΗΛΙΔΗΣ")
    assert third["id"] != first["id"]


def test_person_profile_reuses_latest_passport(tmp_path: Path):
    db = Database(tmp_path / "db.sqlite3")
    pid = db.get_or_create_person("HOXHA", "ARBEN", "02/01/1980")
    db.add_action(pid, "REFUSAL", protocol_no="P1", passport_no="OLD")
    db.add_action(pid, "FINE_IMPOSITION", protocol_no="P2", passport_no="NEW")
    p = db.person_profile(pid)
    assert p["surname"] == "HOXHA" and p["given_name"] == "ARBEN"
    assert p["passport_no"] == "NEW" and p["actions_count"] == 2
