from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from app.docgen.refusals import REFUSAL_REASONS, RefusalDocumentEngine, RefusalEntry, refusal_checkbox_markers


def _text(path: Path) -> str:
    with ZipFile(path) as z:
        root=ET.fromstring(z.read("word/document.xml"))
    ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return "".join((n.text or "") for n in root.findall(".//w:t",ns))


def test_every_refusal_reason_has_exact_checkbox_mapping_and_renders_tick(tmp_path: Path):
    expected={
        "A":("Α",),"B":("Β",),"G":("Γ","C"),"D":("Δ","D"),"E":("Ε",),
        "F":("ΣΤ","F"),"Z":("Z","G"),"H":("H",),
    }
    engine=RefusalDocumentEngine(Path("resources/Master_Template_Arnisi.docx"))
    for idx,reason in enumerate(REFUSAL_REASONS):
        if reason.startswith("I-") and "ΒΙΟΜΕΤΡΙΚ" in reason:
            assert refusal_checkbox_markers(reason)==("Ι",)
        elif reason.startswith("I-"):
            assert refusal_checkbox_markers(reason)==("Θ","I")
        else:
            assert refusal_checkbox_markers(reason)==expected[reason[0]]
        entry=RefusalEntry(
            aa=str(idx+1),year="2026",protocol_prefix="1",protocol_no=str(idx+1),
            date="26-09-2026",time="10:00",sex="M",surname="TEST",name="PERSON",
            birth_date="01-01-1990",passport="X1",issue_date="01-01-2025",reason=reason,
            birth_place="TEST",nationality="TEST",residence="TEST",
            passport_issuer="TEST",origin_country="TEST",
        )
        out=tmp_path/f"r{idx}.docx"; engine.create(out,entry)
        text=_text(out)
        assert "☒" in text
        assert "?" not in text
