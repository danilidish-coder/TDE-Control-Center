from pathlib import Path

def test_refusal_defaults_are_present_and_editable_lines():
    text = Path("app/ui/refusals_page.py").read_text(encoding="utf-8")
    for needle in (
        "line('birth_place','ΑΛΒΑΝΙΑ')",
        "line('nationality','ΑΛΒΑΝΙΚΗ')",
        "line('passport_issuer','ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ')",
        "line('origin_country','ΑΛΒΑΝΙΑ (ALBANIA)')",
        "self.f['birth_place'].setText('ΑΛΒΑΝΙΑ')",
        "self.f['nationality'].setText('ΑΛΒΑΝΙΚΗ')",
        "self.f['passport_issuer'].setText('ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ')",
        "self.f['origin_country'].setText('ΑΛΒΑΝΙΑ (ALBANIA)')",
    ):
        assert needle in text

def test_fines_uses_generic_responsible_label():
    text = Path("app/ui/fines_page.py").read_text(encoding="utf-8")
    assert "ΑΣΤΥΝΟΜΙΚΟΣ / ΑΡΜΟΔΙΟΣ" in text
    assert "Αστυνομικός / Αρμόδιος" in text
    assert "['Τύπος','Ημερομηνία','Επώνυμο','Όνομα','Ποσό','Πρωτόκολλο','Εισπράττων']" not in text

def test_archive_labels_are_generic():
    assert "Αστυνομικός / Αρμόδιος" in Path("app/ui/fines_archive.py").read_text(encoding="utf-8")
    assert "Αστυνομικός / Αρμόδιος" in Path("app/ui/person_archive.py").read_text(encoding="utf-8")
