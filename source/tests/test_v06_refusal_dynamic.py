from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from app.core.db import Database
from app.docgen.refusals import REFUSAL_REASONS, RefusalDocumentEngine, RefusalEntry, vas_entry_text


def _doc_text(path: Path) -> str:
    with ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return "".join((n.text or "") for n in root.findall(".//w:t", ns))


def test_non_albanian_refusal_identity_is_dynamic(tmp_path: Path):
    db = Database(tmp_path / "db.sqlite3")
    with db.connect() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(refusals)").fetchall()}
    assert {"birth_place","nationality","residence","passport_issuer","origin_country"} <= cols

    entry = RefusalEntry(
        aa="1", year="2026", protocol_prefix="123", protocol_no="456",
        date="26-09-2026", time="10:30", sex="M", surname="TEST", name="PERSON",
        birth_date="01-01-1990", passport="TR123456", issue_date="01-01-2025",
        reason=REFUSAL_REASONS[0], language="ΑΓΓΛΙΚΑ",
        birth_place="ΤΟΥΡΚΙΑ", nationality="ΤΟΥΡΚΙΚΗ", residence="ΚΩΝΣΤΑΝΤΙΝΟΥΠΟΛΗ",
        passport_issuer="ΤΟΥΡΚΙΚΕΣ ΑΡΧΕΣ", origin_country="ΤΟΥΡΚΙΑ",
    )
    output = tmp_path / "refusal.docx"
    RefusalDocumentEngine(Path("resources/Master_Template_Arnisi.docx")).create(output, entry)
    text = _doc_text(output)

    for expected in ("ΤΟΥΡΚΙΑ", "ΤΟΥΡΚΙΚΗ", "ΚΩΝΣΤΑΝΤΙΝΟΥΠΟΛΗ", "ΤΟΥΡΚΙΚΕΣ ΑΡΧΕΣ"):
        assert expected in text
    assert "ΑΛΒΑΝΙΚΗ" not in text
    assert "ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ" not in text
    assert "ΑΛΒΑΝΙΑ" not in text

    vas = vas_entry_text(entry)
    assert "εθνικότητα ΤΟΥΡΚΙΚΗ" in vas
    assert "αριθμός διαβατηρίου TR123456" in vas
    assert "Αλβανικού" not in vas
