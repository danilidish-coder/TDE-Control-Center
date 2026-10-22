from __future__ import annotations

import copy
import shutil
import tempfile
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile
from lxml import etree

from app.shared.payments import payment_category
from app.shared.documents.common import clean, fmt_date
from app.shared.documents.docx_mirror import NS, W, _extract, _pack, cell_text, set_cell_text, replace_sequence, replace_sequence_occurrence

ALLOWED_AMOUNTS = {600, 1200}
COLLECTION_METHODS = ("e-ΠΑΡΑΒΟΛΟ", "ΕΦΟΡΙΑ", "ΧΡΗΜ ΠΟΣΟ")

@dataclass(frozen=True)
class FineEntry:
    date: str
    imposition_protocol: str = ""
    paravolo: str = ""
    surname: str = ""
    name: str = ""
    birth_date: str = ""
    nationality: str = ""
    passport: str = ""
    measure: str = ""
    amount: int = 0
    collection_method: str = ""
    collection_protocol: str = ""
    responsible: str = ""

    @property
    def is_imposition(self) -> bool:
        # Exact VBA rule: imposition iff BOTH paravolo and collection method are empty.
        return not clean(self.paravolo) and not clean(self.collection_method)

    def validate(self) -> None:
        # Exact VBA validation: only surname + allowed fine amount are mandatory.
        # Name may be blank; do not add stricter validation than the workbook macro.
        if not clean(self.surname):
            raise ValueError("Απαιτείται Επώνυμο.")
        if int(self.amount) not in ALLOWED_AMOUNTS:
            raise ValueError("Χρηματικό ποσό: επιτρέπεται μόνο 600 ή 1200.")
        fmt_date(self.date, "/")
        if clean(self.birth_date):
            fmt_date(self.birth_date, "/")

    def report_row(self) -> list[str]:
        self.validate()
        if self.is_imposition:
            return [
                fmt_date(self.date, "/"), clean(self.imposition_protocol), clean(self.surname), clean(self.name),
                fmt_date(self.birth_date, "/"), clean(self.nationality), clean(self.passport), clean(self.measure),
                str(int(self.amount)), clean(self.responsible) or "AX. YPIRESIAAS", "",
            ]
        return [
            fmt_date(self.date, "/"), clean(self.collection_protocol), clean(self.surname), clean(self.name),
            fmt_date(self.birth_date, "/"), clean(self.nationality), clean(self.passport), clean(self.measure),
            str(int(self.amount)), clean(self.paravolo) or "EISPRAXI", clean(self.responsible) or "AX. YPIRESIAAS",
        ]

    def daily_identity(self) -> str:
        amount = str(int(self.amount))
        if self.is_imposition:
            return f"EPIVOLI_{amount}"
        method = clean(self.collection_method)
        prefix = {"payment": "EISPRAXI", "eparavolo": "EPARAVOLO", "detypa": "TYPOU_A"}.get(payment_category(method))
        if prefix:
            return f"{prefix}_{amount}"
        raise ValueError(f"Δεν αναγνωρίστηκε ο τρόπος είσπραξης: {method}")


class FineReportEngine:
    def __init__(self, base_docx: str | Path):
        self.base_docx = Path(base_docx)
        if not self.base_docx.is_file():
            raise FileNotFoundError(self.base_docx)

    def create_report(self, output_docx: str | Path, *, officer_name: str, officer_agms: str,
                      operational_day: date | None = None, start_dt: datetime | None = None,
                      end_dt: datetime | None = None, officer_rank_short: str = "Ανθ/μου",
                      officer_rank_full: str = "ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ") -> Path:
        """Compatibility entry requiring an explicit recorded time window."""
        if start_dt is None or end_dt is None:
            raise ValueError("Απαιτούνται οι πραγματικές ώρες έναρξης και λήξης της βάρδιας.")
        return self.create_report_window(
            output_docx, officer_name=officer_name, officer_agms=officer_agms,
            start_dt=start_dt, end_dt=end_dt, officer_rank_short=officer_rank_short,
            officer_rank_full=officer_rank_full,
        )

    def create_report_window(self, output_docx: str | Path, *, officer_name: str, officer_agms: str,
                             start_dt: datetime, end_dt: datetime,
                             officer_rank_short: str = "Ανθ/μου",
                             officer_rank_full: str = "ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ",
                             electronically_signed: bool = False,
                             signed_at: datetime | None = None, active: bool = False) -> Path:
        """Create a clean live Anafora for an explicitly approved date/time window.

        This is the first deliberate deviation from the VBA workflow: the operator may
        choose the exact start/end date and time when starting a new live report.  The
        document itself remains the exact supplied VBA-era layout.
        """
        if end_dt < start_dt:
            raise ValueError("Η λήξη της αναφοράς δεν μπορεί να είναι πριν από την έναρξη.")
        output = Path(output_docx)
        with tempfile.TemporaryDirectory() as td0:
            td = Path(td0)
            _extract(self.base_docx, td)
            xml_path = td / "word" / "document.xml"
            root = etree.fromstring(xml_path.read_bytes())
            # The packaged base is privacy-neutral.  Keep backward compatibility
            # with the original literal-based reference during QA/recovery.
            if replace_sequence(root, "[RANK_SHORT]", clean(officer_rank_short) or "Ανθ/μου") == 0:
                replace_sequence(root, "Ανθ/μου", clean(officer_rank_short) or "Ανθ/μου")
            agms = clean(officer_agms)
            officer_name_display = clean(officer_name).upper()
            signature_detail = clean(officer_rank_full).upper()
            if agms:
                signature_detail = f"{signature_detail} - ΑΓΜΣ {agms}"
            if active:
                signature_detail += " | ΠΡΟΕΠΙΣΚΟΠΗΣΗ — ΕΝΕΡΓΗ ΒΑΡΔΙΑ (προσωρινή λήξη)."
            if electronically_signed:
                signature_detail += " | Η εφαρμογή έκλεισε"
                if signed_at is not None:
                    signature_detail += f" στις {signed_at.strftime('%d/%m/%Y %H:%M')}"
                signature_detail += "."
            if replace_sequence(root, "[AGMS]", "") == 0:
                replace_sequence(root, "268862", "")
            if replace_sequence(root, "[OFFICER_NAME]", officer_name_display) == 0:
                replace_sequence(root, "ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ", officer_name_display)

            if replace_sequence(root, "[START_DATE]", start_dt.strftime("%d/%m/%Y")) == 0:
                replace_sequence(root, "15/09/2026", start_dt.strftime("%d/%m/%Y"))
            if replace_sequence(root, "[END_DATE]", end_dt.strftime("%d/%m/%Y")) == 0:
                replace_sequence(root, "16/09/2026", end_dt.strftime("%d/%m/%Y"))
            if replace_sequence(root, "[END_FOOTER_DATE]", end_dt.strftime("%d/%m/ %Y")) == 0:
                replace_sequence(root, "16/09/ 2026", end_dt.strftime("%d/%m/ %Y"))

            start_count = replace_sequence(root, "[START_TIME]", start_dt.strftime("%H:%M"))
            end_count = replace_sequence(root, "[END_TIME]", end_dt.strftime("%H:%M"))
            if start_count == 0 and end_count == 0:
                # Legacy template fallback: both values were the literal 10:00.
                if not replace_sequence_occurrence(root, "10:00", end_dt.strftime("%H:%M"), 2):
                    raise ValueError("Δεν βρέθηκε η ώρα λήξης στο πρότυπο Αναφοράς.")
                if not replace_sequence_occurrence(root, "10:00", start_dt.strftime("%H:%M"), 1):
                    raise ValueError("Δεν βρέθηκε η ώρα έναρξης στο πρότυπο Αναφοράς.")

            if replace_sequence(root, "[RANK_FULL]", signature_detail) == 0:
                replace_sequence(root, "ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ", signature_detail)
            xml_path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes"))
            _pack(td, output)
        return output

    @staticmethod
    def _find_collection_header(rows) -> int:
        for i, row in enumerate(rows):
            cells = row.xpath("./w:tc", namespaces=NS)
            if len(cells) >= 2 and "Είσπραξης" in cell_text(cells[1]):
                return i
        raise ValueError("Λείπει η ενότητα Είσπραξης από την αναφορά.")

    @staticmethod
    def _blank_data_row(row) -> bool:
        cells = row.xpath("./w:tc", namespaces=NS)
        return len(cells) >= 3 and not cell_text(cells[2])

    @staticmethod
    def _clone_row_before(table, rows, index: int, sample_index: int) -> None:
        # ``w:tbl`` contains non-row children (tblPr/tblGrid) before ``w:tr``.
        # Inserting by a raw child index therefore shifts the new row to the wrong
        # table position after repeated growth.  Word VBA's Rows.Add BeforeRow:=...
        # is row-relative, so mirror it by inserting directly before the target w:tr.
        rows[index].addprevious(copy.deepcopy(rows[sample_index]))

    @staticmethod
    def _clone_row_after(table, rows, sample_index: int) -> None:
        table.append(copy.deepcopy(rows[sample_index]))

    @staticmethod
    def _format_collections(table) -> None:
        """Format only the receipts rows with native Word table properties.

        Word table cells have no interoperable rounded-corner setting. Avoid
        floating drawings that would obscure fields or fail during printing.
        """
        rows = table.xpath("./w:tr", namespaces=NS)
        first = FineReportEngine._find_collection_header(rows)
        def child(parent, name):
            found = parent.find(f"{{{W}}}{name}")
            return found if found is not None else etree.SubElement(parent, f"{{{W}}}{name}")
        for index, row in enumerate(rows[first:]):
            for cell in row.xpath("./w:tc", namespaces=NS):
                properties = child(cell, "tcPr")
                child(properties, "vAlign").set(f"{{{W}}}val", "center")
                margins = child(properties, "tcMar")
                for side in ("top", "left", "bottom", "right"):
                    edge = child(margins, side)
                    edge.set(f"{{{W}}}w", "50")
                    edge.set(f"{{{W}}}type", "dxa")
                borders = child(properties, "tcBorders")
                for side in ("top", "left", "bottom", "right"):
                    edge = child(borders, side)
                    for key, value in (("val", "single"), ("sz", "4"), ("color", "9BAAB5")):
                        edge.set(f"{{{W}}}{key}", value)
                shading = child(properties, "shd")
                shading.set(f"{{{W}}}val", "clear")
                shading.set(f"{{{W}}}fill", "E8EEF3" if index == 0 else ("F6F8FA" if index % 2 else "FFFFFF"))
                for paragraph in cell.xpath(".//w:p", namespaces=NS):
                    spacing = child(child(paragraph, "pPr"), "spacing")
                    spacing.set(f"{{{W}}}before", "0")
                    spacing.set(f"{{{W}}}after", "0")
                    for run in paragraph.xpath("./w:r", namespaces=NS):
                        child(run, "rPr")
                    for props in paragraph.xpath(".//w:rPr", namespaces=NS):
                        fonts = child(props, "rFonts")
                        for alphabet in ("ascii", "hAnsi", "cs", "eastAsia"):
                            fonts.set(f"{{{W}}}{alphabet}", "Times New Roman")
                        for size in ("sz", "szCs"):
                            child(props, size).set(f"{{{W}}}val", "16")
                        child(props, "b").set(f"{{{W}}}val", "1" if index == 0 else "0")

    def write_entries(self, output_docx: str | Path, entries: Iterable[FineEntry], *, source_docx: str | Path | None = None) -> Path:
        source = Path(source_docx) if source_docx else self.base_docx
        output = Path(output_docx)
        with tempfile.TemporaryDirectory() as td0:
            td = Path(td0)
            _extract(source, td)
            xml_path = td / "word" / "document.xml"
            root = etree.fromstring(xml_path.read_bytes())
            table = root.xpath("//w:tbl", namespaces=NS)[0]
            for entry in entries:
                vals = entry.report_row()
                rows = table.xpath("./w:tr", namespaces=NS)
                collection = self._find_collection_header(rows)
                indexes = range(1, collection) if entry.is_imposition else range(collection + 1, len(rows))
                target = next((i for i in indexes if self._blank_data_row(rows[i])), None)
                if target is None:
                    if entry.is_imposition:
                        # Word VBA inserts a row immediately before the collection header.
                        sample = max(1, collection - 1)
                        self._clone_row_before(table, rows, collection, sample)
                        rows = table.xpath("./w:tr", namespaces=NS)
                        target = collection
                    else:
                        # Word VBA appends a row at the end of the table.
                        sample = len(rows) - 1
                        self._clone_row_after(table, rows, sample)
                        rows = table.xpath("./w:tr", namespaces=NS)
                        target = len(rows) - 1
                cells = rows[target].xpath("./w:tc", namespaces=NS)
                if len(cells) != 11:
                    raise ValueError("Η αναφορά Προστίμων πρέπει να έχει 11 στήλες.")
                for tc, value in zip(cells, vals):
                    set_cell_text(tc, value)
            self._format_collections(table)
            xml_path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes"))
            _pack(td, output)
        return output
