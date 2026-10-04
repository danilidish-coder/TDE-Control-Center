from __future__ import annotations

import copy
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile
from lxml import etree

from .common import clean, fmt_date
from .docx_mirror import NS, W, _extract, _pack, replace_sequence, replace_sequence_occurrence
from .refusal_languages import LANGUAGES, replacements as language_replacements

REFUSAL_REASONS = (
    "A-ΕΛΛΕΙΨΗ ΕΓΚΥΡΟΥ ΤΑΞ. ΕΓΓΡΑΦΟΥ",
    "B-ΠΛΑΣΤΟ 'Η ΠΑΡΑΠΟΙΗΜΕΝΟ ΤΑΞ. ΕΓΓΡΑΦΟ",
    "G-ΕΛΛΕΙΨΗ ΕΓΚΥΡΗΣ ΘΕΩΡΗΣΗΣ Η' ΤΙΤΛΟΥ ΔΙΑΜΟΝΗΣ",
    "D-ΠΛΑΣΤΗ Ή ΠΑΡΑΠ/ΝΗ ΘΕΩΡΗΣΗ 'Η ΤΙΤΛΟ ΔΑΜΟΝΗΣ",
    "E-ΣΚΟΠΟΣ ΤΑΞΙΔΙΟΥ ΚΑΙ ΔΙΑΜΟΝΗΣ",
    "F-ΛΗΞΗ ΔΙΚ. ΧΡΟΝΟΥ-ΕΛΛΕΙΨΗ ΣΦΡΑΓΙΔΑΣ ΕΞΟΔΟΥ",
    "F-ΛΗΞΗ ΔΙΚ. ΧΡΟΝΟΥ",
    "Z-ΜΕΣΑ ΔΙΑΒΙΩΣΗΣ",
    "H-SIS", "H-SIS-ΔΚΑ", "H-(ΔΚΑ)-ΔΙΟΙΚΗΤΙΚΗ ΑΠΕΛΑΣΗ",
    "H-(ΔΚΑ)-ΔΙΚΑΣΤΙΚΗ ΑΠΕΛΑΣΗ", "H-(ΔΚΑ)-ΠΡΟΣΤΙΜΟ",
    "I-ΕΠΙΚΙΝΔΥΝΟ ΑΤΟΜΟ", "H-ΔΚΑ", "I-ΑΡΝΗΣΗ ΒΙΟΜΕΤΡΙΚΩΝ",
)

@dataclass(frozen=True)
class RefusalEntry:
    aa: str
    year: str
    protocol_prefix: str
    protocol_no: str
    date: str
    time: str
    sex: str
    surname: str
    name: str
    birth_date: str
    passport: str
    issue_date: str
    reason: str
    measure_country: str = ""
    measure_no: str = ""
    measure_from: str = ""
    measure_to: str = ""
    sis_country: str = ""
    sis_no: str = ""
    sis_from: str = ""
    sis_to: str = ""
    language: str = "ΑΛΒΑΝΙΚΑ"

    @property
    def protocol_page1(self) -> str:
        return f"{clean(self.aa)}/{clean(self.year)}"

    @property
    def protocol_page2(self) -> str:
        return f"{clean(self.protocol_prefix)}/{clean(self.protocol_no)}"

    def validate(self) -> None:
        for label, value in (("Α/Α", self.aa), ("Έτος", self.year), ("Πρωτόκολλο", self.protocol_prefix),
                             ("Αριθμός πρωτοκόλλου", self.protocol_no), ("Επώνυμο", self.surname),
                             ("Όνομα", self.name), ("Λόγος άρνησης", self.reason)):
            if not clean(value):
                raise ValueError(f"Απαιτείται {label}.")
        fmt_date(self.date, "-")
        if clean(self.birth_date): fmt_date(self.birth_date, "-")
        if clean(self.issue_date): fmt_date(self.issue_date, "-")
        for value in (self.measure_from, self.measure_to, self.sis_from, self.sis_to):
            if clean(value): fmt_date(value, "-")
        refusal_letters(self.reason)  # validates code
        if clean(self.language).upper() not in LANGUAGES:
            raise ValueError("Μη υποστηριζόμενη γλώσσα άρνησης.")

    def notes(self) -> str:
        def part(kind: str, no: str, country: str, start: str, end: str) -> str:
            if not clean(no): return ""
            s = f"{kind} ({clean(no)}"
            if clean(country): s += f" - {clean(country)}"
            s += f" από {fmt_date(start, '-')} έως {fmt_date(end, '-')})"
            return s
        sis = part("SIS", self.sis_no, self.sis_country, self.sis_from, self.sis_to)
        dka = part("ΔΚΑ", self.measure_no, self.measure_country, self.measure_from, self.measure_to)
        return f"{sis} ΚΑΙ {dka}" if sis and dka else (sis or dka)


def refusal_letters(reason: str) -> tuple[str, str, str]:
    s = clean(reason).upper()
    if s.startswith("ΣΤ"):
        return "ΣΤ", "F", "F"
    ch = s[:1]
    mapping = {
        "A": ("Α", "A", "A"), "Α": ("Α", "A", "A"),
        "B": ("Β", "B", "B"), "Β": ("Β", "B", "B"),
        "G": ("Γ", "C", "C"), "Γ": ("Γ", "C", "C"),
        "D": ("Δ", "D", "D"), "Δ": ("Δ", "D", "D"),
        "E": ("Ε", "E", "E"), "Ε": ("Ε", "E", "E"),
        "F": ("ΣΤ", "F", "F"),
        "Z": ("Ζ", "Z", "G"), "Ζ": ("Ζ", "Z", "G"),
        "H": ("Η", "H", "H"), "Η": ("Η", "H", "H"),
        "I": ("Ι", "J", "J"), "Ι": ("Ι", "J", "J"),
    }
    if ch not in mapping:
        raise ValueError("Ο λόγος άρνησης δεν αναγνωρίστηκε.")
    return mapping[ch]


def activity_cell(reason: str, measure_no: str = "", sis_no: str = "") -> str:
    gr, _, _ = refusal_letters(reason)
    direct = {"Α":"B11","Β":"B12","Γ":"B13","Δ":"B14","Ε":"B15","ΣΤ":"B16","Ζ":"B17","Ι":"B25"}
    if gr in direct: return direct[gr]
    if gr == "Η":
        if clean(measure_no) and clean(sis_no): return "B21"
        if clean(measure_no): return "B19"
        if clean(sis_no): return "B20"
        raise ValueError("Η άρνηση Η απαιτεί ΔΚΑ ή/και SIS.")
    raise ValueError("Μη αναγνωρισμένος λόγος άρνησης.")


class RefusalDocumentEngine:
    def __init__(self, template: str | Path):
        self.template = Path(template)
        if not self.template.is_file(): raise FileNotFoundError(self.template)

    def create(self, output: str | Path, entry: RefusalEntry) -> Path:
        entry.validate()
        output = Path(output)
        gr, lat, alb = refusal_letters(entry.reason)
        with tempfile.TemporaryDirectory() as td0:
            td = Path(td0); _extract(self.template, td)
            xml = td / "word" / "document.xml"
            root = etree.fromstring(xml.read_bytes())
            replacements = {
                "[Α/Α]": entry.protocol_page1,
                "[ΑΡ. ΠΡΩΤ]": entry.protocol_page1,
                "[ΑΡ.ΠΡΩΤΟΚ]": entry.protocol_page2,
                "[ΑΡ. ΠΡΩΤΟΚ]": entry.protocol_page2,
                "[ΑΡ] /[ΠΡ]": entry.protocol_page2,
                "[ΑΡ]": clean(entry.protocol_prefix), "[ΠΡ]": clean(entry.protocol_no),
                "[ΗΜΕΡΟΜΗΝΙΑ ]": fmt_date(entry.date, "-"),
                "[ ΗΜΕΡΟΜΗΝΙΑ  ]": fmt_date(entry.date, "-"),
                "[ΗΜΕΡΟΜΗΝΙΑ]": fmt_date(entry.date, "-"),
                "[ΩΡΑ]": clean(entry.time), "[ΑΕ]":"", "[Ε I]":"", "[ΗΕ]":"", "[ΗΛ]":"", "SIS-ΔΚΑ":"",
                "[ΛΟΓΟΣ ΑΡΝΗΣΗΣ]": clean(entry.reason), "[ΛΑ]": clean(entry.reason),
                "[ΗΜ ΓΕΝΝΗΣΗΣ]": fmt_date(entry.birth_date, "-"),
                "[ΗΜΕΡΟΜΗΝΙΑ ΓΕΝΝΗΣΗΣ]": fmt_date(entry.birth_date, "-"),
                "[ΗΜΕΡΟΜΗΝΙΑ ΓΕΝΝΗΣΗΣ": fmt_date(entry.birth_date, "-"),
                "[ΑΡΙΘΜ. ΔΙΑΒΑΤΗΡΙΟΥ]": clean(entry.passport), "[ΑΡΙΘΜΟΣ ΔΙΑΒΑΤΗΡΙΟΥ]": clean(entry.passport),
                "[ΗΜΕΡΟΜΗΝΙΑ ΕΚΔΟΣΗΣ]": fmt_date(entry.issue_date, "-"),
                "[ΕΠΩΝΥΜΟ]": clean(entry.surname), "[ΟΝΟΜΑ]": clean(entry.name), "[ΦΥΛΟ]": clean(entry.sex),
                "[ΥΠΗΚΟΟΤΗΤΑ]": "ΑΛΒΑΝΙΚΗ", "[ΑΡΙΘΜΟΣ ΜΕΤΡΟΥ]": clean(entry.measure_no), "[SIS]": clean(entry.sis_no),
                # IMPORTANT: VBA output currently leaves [ΗΜΕΡΟ] literal on page 2; preserve that exact behavior.
            }
            for old, new in replacements.items():
                replace_sequence(root, old, new)
            for old, new in language_replacements(entry.language).items():
                replace_sequence(root, old, new)
            for letter in "ABCDEFGHIJ":
                replace_sequence(root, f"({letter})", "☒" if letter in {lat, alb} else "?")
            replace_sequence(root, "[ΠΑΡΑΤΗΡΗΣΕΙΣ]", entry.notes() + " | Λόγος: " + clean(entry.reason), bold=True)
            xml.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes"))
            _pack(td, output)
        return output


def vas_entry_text(entry: RefusalEntry) -> str:
    return (f"(ΕΠ.) {clean(entry.surname)} (ΟΝ.) {clean(entry.name)}, ημ. γεν. {fmt_date(entry.birth_date, '-')}, "
            f"εθνικότητα ΑΛΒΑΝΙΚΗ, αριθμός κοινού Αλβανικού διαβατηρίου {clean(entry.passport)}, "
            f"λόγω {clean(entry.reason)} (Ατομικός φάκελος {entry.protocol_page2}).")

class VasReportEngine:
    """Builds the daily VAS report from the real report's paragraph styles."""
    def __init__(self, reference_docx: str | Path):
        self.reference = Path(reference_docx)
        if not self.reference.is_file(): raise FileNotFoundError(self.reference)

    @staticmethod
    def _paragraph_text(p) -> str:
        return ''.join(p.xpath('.//w:t/text()', namespaces=NS))

    @staticmethod
    def _set_paragraph_text(p, text: str) -> None:
        ts=p.xpath('.//w:t',namespaces=NS)
        if ts:
            # Keep the three-run split used by the original entry where possible.
            if len(ts)>=3 and text.startswith('(ΕΠ.) ') and ', ημ. γεν. ' in text:
                prefix,rest=text.split(', ημ. γεν. ',1)
                ts[0].text=prefix+', '
                ts[1].text='ημ'
                ts[2].text='. γεν. '+rest
                for t in ts[3:]:t.text=''
            else:
                ts[0].text=text
                for t in ts[1:]:t.text=''
        else:
            r=etree.SubElement(p,f'{{{W}}}r');t=etree.SubElement(r,f'{{{W}}}t');t.text=text

    def create(self, output: str | Path, entries: Iterable[RefusalEntry], start_date: str, end_date: str,
               start_time: str = "10:00", end_time: str = "10:00") -> Path:
        output=Path(output)
        with tempfile.TemporaryDirectory() as td0:
            td=Path(td0);_extract(self.reference,td)
            xml=td/'word'/'document.xml';root=etree.fromstring(xml.read_bytes());body=root.find('w:body',namespaces=NS)
            paras=body.xpath('./w:p',namespaces=NS)
            intro=next(p for p in paras if self._paragraph_text(p).startswith('Κατά το χρονικό'))
            entry_tpl=next(p for p in paras if self._paragraph_text(p).startswith('[ENTRY_TEMPLATE]') or self._paragraph_text(p).startswith('(ΕΠ.) '))
            sep_tpl=next(p for p in paras if self._paragraph_text(p).startswith('---'))
            note_tpl=next(p for p in paras if self._paragraph_text(p).startswith('[NOTE_TEMPLATE]') or self._paragraph_text(p).startswith('ΣΗΜΕΙΩΣΗ:'))
            # Delete all operational entry/separator/note paragraphs, preserving title/intro/section.
            for p in list(body.xpath('./w:p',namespaces=NS)):
                txt=self._paragraph_text(p)
                if txt.startswith('[ENTRY_TEMPLATE]') or txt.startswith('[NOTE_TEMPLATE]') or txt.startswith('(ΕΠ.) ') or txt.startswith('---') or txt.startswith('ΣΗΜΕΙΩΣΗ:'):
                    body.remove(p)
            # The supplied live VAS has no blank paragraph between the intro and
            # first entry. Remove only trailing blank paragraphs after the intro.
            intro_index=body.index(intro)
            for p in list(body.xpath('./w:p',namespaces=NS)):
                if body.index(p)>intro_index and not self._paragraph_text(p).strip():
                    body.remove(p)
            # Replace the privacy-neutral runtime markers.  Keep a legacy fallback
            # for the original dated reference used only by regression tests.
            start_fmt = fmt_date(start_date,'-')
            end_fmt = fmt_date(end_date,'-')
            start_fmt = start_fmt[1:] if start_fmt.startswith('0') else start_fmt
            end_fmt = end_fmt[1:] if end_fmt.startswith('0') else end_fmt
            marker_dates = replace_sequence(root,'[START_DATE]',start_fmt) + replace_sequence(root,'[END_DATE]',end_fmt)
            marker_times = replace_sequence(root,'[START_TIME]',clean(start_time)) + replace_sequence(root,'[END_TIME]',clean(end_time))
            if marker_dates == 0 or marker_times == 0:
                old=self._paragraph_text(intro)
                import re as _re
                if marker_dates == 0:
                    dates=_re.findall(r'\d{1,2}-\d{2}-\d{4}',old)
                    if len(dates)>=2:
                        replace_sequence(root,dates[0],start_fmt)
                        replace_sequence(root,dates[1],end_fmt)
                if marker_times == 0:
                    times=_re.findall(r'\b\d{1,2}:\d{2}\b',old)
                    if len(times)>=2:
                        if times[1] == times[0]:
                            replace_sequence_occurrence(root,times[1],clean(end_time),2)
                            replace_sequence_occurrence(root,times[0],clean(start_time),1)
                        else:
                            replace_sequence_occurrence(root,times[0],clean(start_time),1)
                            replace_sequence_occurrence(root,times[1],clean(end_time),1)
            sect=body.find('w:sectPr',namespaces=NS)
            insert_at=len(body) if sect is None else body.index(sect)
            entry_list=list(entries)
            for idx,e in enumerate(entry_list):
                p=copy.deepcopy(entry_tpl);self._set_paragraph_text(p,vas_entry_text(e));body.insert(insert_at,p);insert_at+=1
                if e.notes():
                    n=copy.deepcopy(note_tpl);self._set_paragraph_text(n,'ΣΗΜΕΙΩΣΗ: '+e.notes());body.insert(insert_at,n);insert_at+=1
                if idx < len(entry_list)-1:
                    sp=copy.deepcopy(sep_tpl);self._set_paragraph_text(sp,'--------------------------------------------------');body.insert(insert_at,sp);insert_at+=1
            xml.write_bytes(etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone='yes'))
            _pack(td,output)
        return output

    def append(self, output: str | Path, entry: RefusalEntry) -> Path:
        """Append one refusal to the live VAS, preserving the existing report.

        This mirrors the VBA workflow more closely than rebuilding the whole file:
        the currently active ``ΒΑΣ_ΣΗΜΕΡΙΝΟ.docx`` remains authoritative and a
        new entry is appended to it.  The exact paragraph styles are cloned from
        the clean VAS reference, while the already-written content is untouched.
        """
        entry.validate()
        output = Path(output)
        if not output.is_file():
            raise FileNotFoundError(output)

        # Read the three paragraph templates from the clean reference.
        with tempfile.TemporaryDirectory() as ref_td0:
            ref_td = Path(ref_td0); _extract(self.reference, ref_td)
            ref_root = etree.fromstring((ref_td/'word'/'document.xml').read_bytes())
            ref_body = ref_root.find('w:body', namespaces=NS)
            ref_paras = ref_body.xpath('./w:p', namespaces=NS)
            entry_tpl = next(p for p in ref_paras if self._paragraph_text(p).startswith('[ENTRY_TEMPLATE]') or self._paragraph_text(p).startswith('(ΕΠ.) '))
            sep_tpl = next(p for p in ref_paras if self._paragraph_text(p).startswith('---'))
            note_tpl = next(p for p in ref_paras if self._paragraph_text(p).startswith('[NOTE_TEMPLATE]') or self._paragraph_text(p).startswith('ΣΗΜΕΙΩΣΗ:'))
            entry_tpl = copy.deepcopy(entry_tpl); sep_tpl = copy.deepcopy(sep_tpl); note_tpl = copy.deepcopy(note_tpl)

        with tempfile.TemporaryDirectory() as td0:
            td = Path(td0); _extract(output, td)
            xml = td/'word'/'document.xml'; root = etree.fromstring(xml.read_bytes())
            body = root.find('w:body', namespaces=NS)
            existing = any(self._paragraph_text(p).startswith('(ΕΠ.) ') for p in body.xpath('./w:p', namespaces=NS))
            sect = body.find('w:sectPr', namespaces=NS)
            insert_at = len(body) if sect is None else body.index(sect)

            if existing:
                sp = copy.deepcopy(sep_tpl); self._set_paragraph_text(sp, '--------------------------------------------------')
                body.insert(insert_at, sp); insert_at += 1

            p = copy.deepcopy(entry_tpl); self._set_paragraph_text(p, vas_entry_text(entry))
            body.insert(insert_at, p); insert_at += 1
            if entry.notes():
                n = copy.deepcopy(note_tpl); self._set_paragraph_text(n, 'ΣΗΜΕΙΩΣΗ: ' + entry.notes())
                body.insert(insert_at, n)

            xml.write_bytes(etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes'))
            _pack(td, output)
        return output
