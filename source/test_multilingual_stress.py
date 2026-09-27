from __future__ import annotations
import tempfile
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from lxml import etree

from modules.refusals_engine import REFUSAL_REASONS, RefusalDocumentEngine, RefusalEntry
from modules.refusal_languages import LANGUAGES, replacements

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "resources" / "Master_Template_Arnisi.docx"

SCENARIOS = (
    dict(surname="TEST", name="ONE", passport="AA123456", measure_no="", sis_no=""),
    dict(surname="PAPADOPOULOS-LONGNAME", name="ALEXANDROS", passport="AB9876543", measure_no="M123", sis_no=""),
    dict(surname="JOVANOVIC", name="ALEKSANDAR", passport="SRB000001", measure_no="", sis_no="SIS999"),
    dict(surname="DE-LA-CRUZ-EXTRA-LONG", name="MARIA ANTONIA", passport="ZZ99999999", measure_no="M999", sis_no="SIS888"),
    dict(surname="ÇËŠĆŽ TEST", name="ÉÈÀÒ", passport="UTF812345", measure_no="M-UTF8", sis_no="S-UTF8"),
    dict(surname="МАКЕДОНСКИ-ТЕСТ", name="АЛЕКСАНДАР", passport="MK123456", measure_no="M777", sis_no="S777"),
)

def make_entry(reason, lang, idx, data):
    return RefusalEntry(
        aa=str(idx+1), year="2026", protocol_prefix="1234", protocol_no=str(1000+idx),
        date="22-09-2026", time="10:30", sex="M", surname=data["surname"], name=data["name"],
        birth_date="01-01-1990", passport=data["passport"], issue_date="01-01-2025",
        reason=reason, measure_country="GR", measure_no=data["measure_no"],
        measure_from="01-01-2026" if data["measure_no"] else "",
        measure_to="01-01-2027" if data["measure_no"] else "",
        sis_country="DE", sis_no=data["sis_no"],
        sis_from="01-02-2026" if data["sis_no"] else "",
        sis_to="01-02-2027" if data["sis_no"] else "",
        language=lang,
    )

def xml_info(path):
    with ZipFile(path) as z:
        names=set(z.namelist())
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        root=etree.fromstring(z.read("word/document.xml"))
    text="".join(root.xpath("//w:t/text()", namespaces=NS))
    sect=root.xpath("//w:sectPr", namespaces=NS)
    return root,text,sect

def main():
    assert replacements("ΑΛΒΑΝΙΚΑ") == {}, "Albanian baseline must have no translation replacements"
    assert len(LANGUAGES) == 6
    assert len(REFUSAL_REASONS) == 16
    engine=RefusalDocumentEngine(TEMPLATE)
    _,_,template_sect=xml_info(TEMPLATE)
    created=0
    failures=[]
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for si,data in enumerate(SCENARIOS):
            for ri,reason in enumerate(REFUSAL_REASONS):
                for lang in LANGUAGES:
                    out=td/f"s{si:02d}_r{ri:02d}_{LANGUAGES.index(lang):02d}.docx"
                    try:
                        e=make_entry(reason,lang,ri,data)
                        engine.create(out,e)
                        root,text,sect=xml_info(out)
                        assert len(sect)==len(template_sect), "section/page setup count changed"
                        for token in ("[Α/Α]","[ΩΡΑ]","[ΕΠΩΝΥΜΟ]","[ΟΝΟΜΑ]","[ΛΟΓΟΣ ΑΡΝΗΣΗΣ]"):
                            assert token not in text, f"unresolved runtime token {token}"
                        assert e.surname in text and e.name in text and e.passport in text
                        if lang != "ΑΛΒΑΝΙΚΑ":
                            assert "REFUZIMI I HYRJES NË KUFI" not in text, f"language header not replaced for {lang}"
                        created += 1
                    except Exception as exc:
                        failures.append((si,ri,lang,reason,repr(exc)))
    print(f"CREATED={created}")
    print(f"EXPECTED={len(SCENARIOS)*len(REFUSAL_REASONS)*len(LANGUAGES)}")
    if failures:
        for x in failures[:30]:
            print("FAIL",x)
        raise SystemExit(f"{len(failures)} failures")
    assert created == 576
    print("STRESS_576=PASS")

if __name__ == "__main__":
    main()
