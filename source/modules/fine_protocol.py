from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .common import clean
from .fines_engine import FineEntry

PROTOCOL_FIRST_ROW = 12
PROTOCOL_FIXED_LAST_ROW = 40
PROTOCOL_FIRST_SUMMARY_ROW = 41
PROTOCOL_SEARCH_LAST_ROW = 2000


@dataclass(frozen=True)
class ProtocolReceipt:
    sequence: int
    protocol_no: str
    amount: int
    collection_method: str
    measure: str
    paravolo: str
    officer_key: str = ""  # legacy audit compatibility only
    op_date: str = ""      # legacy audit compatibility only
    protocol_bucket: str = ""

    @property
    def physical_row(self) -> int:
        # This is exact only for a clean protocol with no pre-existing physical gaps.
        # Production row selection is always read from the workbook itself.
        return PROTOCOL_FIRST_ROW + int(self.sequence) - 1


def receipt_from_fine(entry: FineEntry, sequence: int, *, officer_key: str = "", op_date: str = "") -> ProtocolReceipt:
    if entry.is_imposition:
        raise ValueError("Η επιβολή δεν καταχωρίζεται στο Πρωτόκολλο Είσπραξης.")
    # VBA writes EISPRAXI to the *collection method* when K2 is empty.  F keeps C2.
    return ProtocolReceipt(
        sequence=int(sequence),
        protocol_no=clean(entry.collection_protocol),
        amount=int(entry.amount),
        collection_method=clean(entry.collection_method) or "EISPRAXI",
        measure=clean(entry.measure),
        paravolo=clean(entry.paravolo),
        officer_key=clean(officer_key),
        op_date=clean(op_date),
        protocol_bucket=protocol_bucket_from_responsible(entry.responsible),
    )


def summary_row(receipt_count: int) -> int:
    """Row of 'ΣΥΝ ΧΡΗΜ ΠΟΣΟ' for a clean workbook after VBA-style row growth."""
    n = max(0, int(receipt_count))
    return max(PROTOCOL_FIRST_SUMMARY_ROW, PROTOCOL_FIRST_ROW + n)


def protocol_totals(receipts: Iterable[ProtocolReceipt]) -> dict[str, int]:
    # Exact VBA formulas are independent SUMIFs plus a separate SUM(C...).
    cash = eparavolo = tax = total = 0
    for r in receipts:
        method = clean(r.collection_method).upper()
        amount = int(r.amount)
        total += amount
        if "ΧΡ" in method:
            cash += amount
        if "ΠΑΡ" in method:
            eparavolo += amount
        if "ΕΦΟΡ" in method:
            tax += amount
    return {"cash": cash, "eparavolo": eparavolo, "tax": tax, "total": total}


def protocol_bucket_from_responsible(responsible: str) -> str:
    """Return the dynamic protocol owner key approved for the autonomous build.

    This deliberately replaces the old two-bucket VBA rule (ΠΡΩΤΟΚΟΛΛΟ/gest): every
    responsible surname gets its own protocol workbook.  The exact sheet layout inside
    each workbook is still the original ΠΡΩΤΟΚΟΛΛΟ layout.
    """
    raw = clean(responsible).upper()
    return raw or "ΑΧ. ΥΠΗΡΕΣΙΑΣ"


def protocol_filename_key(responsible: str) -> str:
    raw = protocol_bucket_from_responsible(responsible)
    # Windows-invalid filename characters only; preserve Greek spelling and spaces.
    for ch in '<>:"/\\|?*':
        raw = raw.replace(ch, '_')
    raw = ' '.join(raw.split()).strip(' .')
    return raw or 'ΑΧ. ΥΠΗΡΕΣΙΑΣ'


class ProtocolAdapter(Protocol):
    def append(self, workbook_path: str | Path, entry: FineEntry) -> ProtocolReceipt:
        ...


class MemoryProtocolAdapter:
    """Deterministic simulator for one independent workbook per responsible person."""
    def __init__(self, existing_sequences: dict[str, list[int]] | None = None):
        self.rows: dict[str, list[ProtocolReceipt]] = {}
        for key, seqs in (existing_sequences or {}).items():
            path_key = self._path_key(key)
            self.rows[path_key] = [
                ProtocolReceipt(seq, "", 0, "", "", "", protocol_bucket=str(key))
                for seq in seqs
            ]

    @staticmethod
    def _path_key(workbook_path: str | Path) -> str:
        return str(Path(workbook_path)).casefold()

    def reset(self, workbook_path: str | Path) -> None:
        self.rows.pop(self._path_key(workbook_path), None)

    def append(self, workbook_path: str | Path, entry: FineEntry) -> ProtocolReceipt:
        owner = protocol_bucket_from_responsible(entry.responsible)
        path_key = self._path_key(workbook_path)
        rows = self.rows.setdefault(path_key, [])
        seqs = [r.sequence for r in rows]
        seq = (max(seqs) + 1) if seqs else 1
        base = receipt_from_fine(entry, seq)
        receipt = ProtocolReceipt(
            base.sequence, base.protocol_no, base.amount, base.collection_method,
            base.measure, base.paravolo, base.officer_key, base.op_date, owner,
        )
        rows.append(receipt)
        return receipt


class ExcelComProtocolAdapter:
    """Exact Windows/Excel-COM mirror of the VBA protocol write.

    The workbook is a generated working file copied once from the clean internal
    mirror of the original workbook.  It is not an external user template.
    """
    XL_UP = -4162
    XL_SHIFT_DOWN = -4121
    XL_FORMAT_FROM_LEFT_OR_ABOVE = 0
    XL_MOVE = 2

    def __init__(self, base_workbook: str | Path):
        self.base_workbook = Path(base_workbook)
        if not self.base_workbook.is_file():
            raise FileNotFoundError(self.base_workbook)

    def ensure_workbook(self, workbook_path: str | Path) -> Path:
        p = Path(workbook_path)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.base_workbook, p)
        return p

    @staticmethod
    def _summary_row(ws) -> int | None:
        last_row = int(ws.Cells(ws.Rows.Count, 2).End(ExcelComProtocolAdapter.XL_UP).Row)
        last_row = max(last_row, PROTOCOL_FIRST_SUMMARY_ROW)
        for row in range(PROTOCOL_FIRST_ROW, last_row + 1):
            cell = ws.Cells(row, 3)
            try:
                has_formula = bool(cell.HasFormula)
                formula = str(cell.Formula or "").upper()
            except Exception:
                has_formula = False
                formula = ""
            if has_formula and "SUMIF" in formula:
                return row
        return None

    @staticmethod
    def _blank(value) -> bool:
        return value is None or str(value).strip() == ""

    @staticmethod
    def _next_sequence(ws, row: int) -> int:
        if row <= PROTOCOL_FIRST_ROW:
            return 1
        try:
            # VBA: WorksheetFunction.Max(A12:A(previous)) + 1
            max_value = ws.Application.WorksheetFunction.Max(
                ws.Range(f"A{PROTOCOL_FIRST_ROW}:A{row - 1}")
            )
            return int(max_value) + 1
        except Exception:
            vals = []
            for r in range(PROTOCOL_FIRST_ROW, row):
                v = ws.Cells(r, 1).Value2
                try:
                    if not ExcelComProtocolAdapter._blank(v):
                        vals.append(int(v))
                except Exception:
                    pass
            return (max(vals) + 1) if vals else 1

    @staticmethod
    def _find_data_row(ws, summary: int | None) -> tuple[int, int | None]:
        if summary is not None:
            for row in range(PROTOCOL_FIRST_ROW, summary):
                if ExcelComProtocolAdapter._blank(ws.Cells(row, 2).Value2) and ExcelComProtocolAdapter._blank(ws.Cells(row, 3).Value2):
                    return row, summary
            # VBA makes every signature shape move with cells before inserting.
            for i in range(1, int(ws.Shapes.Count) + 1):
                try:
                    ws.Shapes.Item(i).Placement = ExcelComProtocolAdapter.XL_MOVE
                except Exception:
                    pass
            ws.Rows(summary).Insert(
                Shift=ExcelComProtocolAdapter.XL_SHIFT_DOWN,
                CopyOrigin=ExcelComProtocolAdapter.XL_FORMAT_FROM_LEFT_OR_ABOVE,
            )
            return summary, summary + 1

        # gest/fallback branch: VBA scans B/C for first physically blank row.
        for row in range(PROTOCOL_FIRST_ROW, PROTOCOL_SEARCH_LAST_ROW + 1):
            if ExcelComProtocolAdapter._blank(ws.Cells(row, 2).Value2) and ExcelComProtocolAdapter._blank(ws.Cells(row, 3).Value2):
                return row, None
        raise RuntimeError("Δεν βρέθηκε κενή γραμμή στο Πρωτόκολλο.")

    @staticmethod
    def _refresh_primary_formulas(ws, summary: int, last_data_row: int) -> None:
        # Same formulas as the VBA, moved/extended with each inserted row.
        ws.Cells(summary, 3).Formula = f'=SUMIF(D{PROTOCOL_FIRST_ROW}:D{last_data_row},"*ΧΡ*",C{PROTOCOL_FIRST_ROW}:C{last_data_row})'
        ws.Cells(summary + 1, 3).Formula = f'=SUMIF(D{PROTOCOL_FIRST_ROW}:D{last_data_row},"*ΠΑΡ*",C{PROTOCOL_FIRST_ROW}:C{last_data_row})'
        ws.Cells(summary + 2, 3).Formula = f'=SUMIF(D{PROTOCOL_FIRST_ROW}:D{last_data_row},"*ΕΦΟΡ*",C{PROTOCOL_FIRST_ROW}:C{last_data_row})'
        ws.Cells(summary + 3, 3).Formula = f'=SUM(C{PROTOCOL_FIRST_ROW}:C{last_data_row})'
        ws.Calculate()

    def append(self, workbook_path: str | Path, entry: FineEntry) -> ProtocolReceipt:
        if entry.is_imposition:
            raise ValueError("Η επιβολή δεν γράφεται στο Πρωτόκολλο.")
        p = self.ensure_workbook(workbook_path)
        if platform.system().lower() != "windows":
            raise RuntimeError("Το Πρωτόκολλο μέσω Excel COM απαιτεί Windows.")
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:
            raise RuntimeError("Λείπει το pywin32 από το Windows build.") from exc

        pythoncom.CoInitialize()
        excel = wb = None
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.ScreenUpdating = False
            excel.EnableEvents = False
            try:
                excel.AutomationSecurity = 3
            except Exception:
                pass
            wb = excel.Workbooks.Open(Filename=str(p), UpdateLinks=False, ReadOnly=False, Notify=False)
            if bool(wb.ReadOnly):
                raise PermissionError("Το Πρωτόκολλο άνοιξε μόνο για ανάγνωση.")
            bucket = protocol_bucket_from_responsible(entry.responsible)
            # Autonomous change #2: every responsible person gets a separate workbook,
            # and every workbook uses the exact original ΠΡΩΤΟΚΟΛΛΟ sheet/layout.
            try:
                ws = wb.Worksheets("ΠΡΩΤΟΚΟΛΛΟ")
            except Exception:
                ws = wb.Worksheets(2)

            summary = self._summary_row(ws)
            row, summary = self._find_data_row(ws, summary)
            seq = self._next_sequence(ws, row)
            method_for_protocol = clean(entry.collection_method) or "EISPRAXI"

            ws.Cells(row, 1).Value = seq
            ws.Cells(row, 2).Value = clean(entry.collection_protocol)
            ws.Cells(row, 3).Value = int(entry.amount)
            ws.Cells(row, 4).Value = method_for_protocol
            ws.Cells(row, 5).Value = clean(entry.measure)
            ws.Cells(row, 6).Value = clean(entry.paravolo)

            if summary is not None:
                self._refresh_primary_formulas(ws, summary, row)

            wb.Save()
            # Verify the exact row after Save.
            if int(ws.Cells(row, 1).Value2) != seq:
                raise RuntimeError("Δεν επιβεβαιώθηκε ο Α/Α του Πρωτοκόλλου.")
            wb.Close(SaveChanges=False); wb = None
            return ProtocolReceipt(
                seq, clean(entry.collection_protocol), int(entry.amount), method_for_protocol,
                clean(entry.measure), clean(entry.paravolo), protocol_bucket=bucket,
            )
        finally:
            if wb is not None:
                try: wb.Close(SaveChanges=False)
                except Exception: pass
            if excel is not None:
                try: excel.Quit()
                except Exception: pass
            try: pythoncom.CoUninitialize()  # type: ignore[name-defined]
            except Exception: pass
