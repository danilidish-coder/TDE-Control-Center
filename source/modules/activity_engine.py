from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .common import parse_greek_date
from .fines_engine import FineEntry
from .refusals_engine import RefusalEntry, activity_cell


FINE_ACTIVITY_CELLS: dict[str, str] = {
    "EPIVOLI_600": "D11",
    "EPIVOLI_1200": "D12",
    "EISPRAXI_600": "D15",
    "EISPRAXI_1200": "D16",
    "EPARAVOLO_600": "D17",
    "EPARAVOLO_1200": "D18",
    "TYPOU_A_600": "D19",
    "TYPOU_A_1200": "D20",
}


@dataclass(frozen=True)
class ActivityPlan:
    source: str
    target_cell: str
    key: str
    log_sheet: str
    password: str = "1234"
    event_type: str = ""


@dataclass(frozen=True)
class ActivityResult:
    applied: bool
    duplicate: bool = False
    queued: bool = False
    error: str = ""


def clean_key_part(value: object) -> str:
    """Exact VBA CleanKeyPart semantics used by the fine macro."""
    text = str(value if value is not None else "").strip().upper()
    return text.replace("|", "/").replace("\r", " ").replace("\n", " ")


def fine_transaction_key(entry: FineEntry, receipt_sequence: str = "") -> str:
    try:
        d = parse_greek_date(entry.date)
        date_key = d.strftime("%Y%m%d") if d else clean_key_part(entry.date)
    except Exception:
        date_key = clean_key_part(entry.date)
    amount = str(int(entry.amount))
    if entry.is_imposition:
        return "|".join((
            "EPIVOLI", date_key, clean_key_part(entry.imposition_protocol),
            clean_key_part(entry.surname), amount,
        ))
    return "|".join((
        "EISPRAXI", date_key, clean_key_part(entry.collection_protocol),
        clean_key_part(receipt_sequence), clean_key_part(entry.surname), amount,
        clean_key_part(entry.collection_method),
    ))


def fine_activity_plan(entry: FineEntry, receipt_sequence: str = "") -> ActivityPlan:
    identity = entry.daily_identity()
    try:
        cell = FINE_ACTIVITY_CELLS[identity]
    except KeyError as exc:
        raise ValueError(f"Δεν υπάρχει αντιστοίχιση Ημερήσιας Δραστηριότητας για {identity}.") from exc
    return ActivityPlan("FINE", cell, fine_transaction_key(entry, receipt_sequence), "_AUTO_LOG", event_type=identity)


def refusal_activity_key(entry: RefusalEntry, target_cell: str | None = None) -> str:
    cell = target_cell or activity_cell(entry.reason, entry.measure_no, entry.sis_no)
    # Mirrors BuildRefusalActivityKey: TargetCell + A2:H2, without upper-casing.
    vals = (
        entry.aa, entry.year, entry.protocol_prefix, entry.protocol_no,
        entry.date, entry.time, entry.sex, entry.surname,
    )
    return "REFUSAL|" + cell + "|" + "|".join(str(v if v is not None else "").strip() for v in vals)


def refusal_activity_plan(entry: RefusalEntry) -> ActivityPlan:
    cell = activity_cell(entry.reason, entry.measure_no, entry.sis_no)
    return ActivityPlan("REFUSAL", cell, refusal_activity_key(entry, cell), "AUTO_LOG", event_type="REFUSAL")


class ActivityAdapter(Protocol):
    def increment_once(self, workbook_path: str | Path, plan: ActivityPlan) -> bool:
        """Return True if incremented, False if the key already existed."""
        ...


class MemoryActivityAdapter:
    """Deterministic adapter used for simulations; models the VBA idempotency log."""
    def __init__(self, cells: dict[str, int] | None = None, failures_left: int = 0):
        self.cells = dict(cells or {})
        self.keys: set[tuple[str, str]] = set()
        self.failures_left = failures_left
        self.calls: list[ActivityPlan] = []

    def increment_once(self, workbook_path: str | Path, plan: ActivityPlan) -> bool:
        self.calls.append(plan)
        if self.failures_left > 0:
            self.failures_left -= 1
            raise OSError("SIMULATED_LOCK")
        token = (plan.log_sheet, plan.key)
        if token in self.keys:
            return False
        old = self.cells.get(plan.target_cell, 0)
        if not isinstance(old, (int, float)) or isinstance(old, bool):
            raise ValueError(f"Το κελί {plan.target_cell} δεν περιέχει αριθμό.")
        self.cells[plan.target_cell] = int(old) + 1
        self.keys.add(token)
        return True


class ExcelComActivityAdapter:
    """Windows Excel-COM writer matching the current VBA daily-activity behavior.

    COM is imported lazily, so the autonomous package can still be imported and
    simulated on non-Windows systems.  The production EXE will bundle pywin32.
    """
    XL_VALUES = -4163
    XL_WHOLE = 1
    XL_UP = -4162
    XL_SHEET_VERY_HIDDEN = 2

    def __init__(self, retries: int = 10, delay: float = 1.0):
        self.retries = max(0, int(retries))
        self.delay = max(0.0, float(delay))

    @staticmethod
    def _next_row(ws) -> int:
        row = int(ws.Cells(ws.Rows.Count, 1).End(ExcelComActivityAdapter.XL_UP).Row) + 1
        return max(row, 2)

    @staticmethod
    def _ensure_log(wb, plan: ActivityPlan):
        try:
            ws = wb.Worksheets(plan.log_sheet)
        except Exception:
            ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
            ws.Name = plan.log_sheet
            if plan.source == "FINE":
                headers = (
                    "TRANSACTION_KEY", "TIMESTAMP", "TYPE", "TARGET_CELL",
                    "OLD_VALUE", "NEW_VALUE", "COMPUTER", "EXCEL_USER",
                )
            else:
                headers = ("ActivityKey", "DateTime", "TargetCell", "Source")
            for i, value in enumerate(headers, 1):
                ws.Cells(1, i).Value = value
            ws.Visible = ExcelComActivityAdapter.XL_SHEET_VERY_HIDDEN
        return ws

    def increment_once(self, workbook_path: str | Path, plan: ActivityPlan) -> bool:
        p = Path(workbook_path)
        if not p.is_file():
            raise FileNotFoundError(f"Δεν βρέθηκε ο Πίνακας Ημερήσιας Δραστηριότητας: {p}")
        if platform.system().lower() != "windows":
            raise RuntimeError("Η εγγραφή στην Ημερήσια Δραστηριότητα μέσω Excel COM απαιτεί Windows.")

        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:
            raise RuntimeError("Λείπει το pywin32 από το Windows build.") from exc

        pythoncom.CoInitialize()
        excel = None
        wb = None
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

            last_error: Exception | None = None
            for attempt in range(self.retries + 1):
                try:
                    wb = excel.Workbooks.Open(
                        Filename=str(p), UpdateLinks=False, ReadOnly=False, Notify=False
                    )
                    if bool(wb.ReadOnly):
                        wb.Close(SaveChanges=False); wb = None
                        raise PermissionError("Η Ημερήσια Δραστηριότητα άνοιξε μόνο για ανάγνωση.")
                    break
                except Exception as exc:
                    last_error = exc
                    if wb is not None:
                        try: wb.Close(SaveChanges=False)
                        except Exception: pass
                        wb = None
                    if attempt < self.retries:
                        time.sleep(self.delay)
            if wb is None:
                raise RuntimeError(f"Δεν άνοιξε η Ημερήσια Δραστηριότητα για εγγραφή: {last_error}")

            target = wb.Worksheets(1)
            try:
                target.Unprotect(Password=plan.password)
                target.Protect(Password=plan.password, UserInterfaceOnly=True)
            except Exception:
                # Some deployments have no protection; that must not prevent a valid write.
                pass

            log = self._ensure_log(wb, plan)
            found = log.Columns(1).Find(
                What=plan.key, LookIn=self.XL_VALUES, LookAt=self.XL_WHOLE
            )
            if found is not None:
                wb.Close(SaveChanges=False); wb = None
                return False

            old = target.Range(plan.target_cell).Value2
            if old is None or str(old).strip() == "":
                old_num = 0
            elif isinstance(old, (int, float)) and not isinstance(old, bool):
                old_num = int(old)
            else:
                raise ValueError(f"Το κελί {plan.target_cell} δεν περιέχει αριθμό.")
            new_num = old_num + 1
            target.Range(plan.target_cell).Value2 = new_num
            check = target.Range(plan.target_cell).Value2
            if int(check) != new_num:
                raise RuntimeError(f"Δεν επιβεβαιώθηκε η αύξηση του {plan.target_cell}.")

            row = self._next_row(log)
            if plan.source == "FINE":
                values = (
                    plan.key, datetime.now(), plan.event_type or plan.source, plan.target_cell,
                    old_num, new_num, os.environ.get("COMPUTERNAME", ""),
                    getattr(excel, "UserName", ""),
                )
            else:
                values = (plan.key, datetime.now(), plan.target_cell, "REFUSAL")
            for i, value in enumerate(values, 1):
                log.Cells(row, i).Value = value
            log.Visible = self.XL_SHEET_VERY_HIDDEN
            wb.Save()
            # Verify the cell after Save in the same workbook instance.
            if int(target.Range(plan.target_cell).Value2) != new_num:
                raise RuntimeError(f"Η αποθήκευση του {plan.target_cell} δεν επιβεβαιώθηκε.")
            wb.Close(SaveChanges=False); wb = None
            return True
        finally:
            if wb is not None:
                try: wb.Close(SaveChanges=False)
                except Exception: pass
            if excel is not None:
                try: excel.Quit()
                except Exception: pass
            try: pythoncom.CoUninitialize()  # type: ignore[name-defined]
            except Exception: pass
