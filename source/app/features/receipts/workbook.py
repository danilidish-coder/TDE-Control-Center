from __future__ import annotations

from app.shared.payments import protocol_category_formulas

import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping


_GREEK_WEEKDAYS = {
    0: "Δευτέρα",
    1: "Τρίτη",
    2: "Τετάρτη",
    3: "Πέμπτη",
    4: "Παρασκευή",
    5: "Σάββατο",
    6: "Κυριακή",
}


def _set_shape_text(ws, name: str, text: str) -> None:
    try:
        shape = ws.Shapes.Item(name)
        try:
            shape.TextFrame2.TextRange.Text = text
        except Exception:
            shape.TextFrame.Characters().Text = text
    except Exception:
        pass


class ProtocolWorkbookWriter:
    def __init__(self, base_workbook: str | Path):
        self.base_workbook = Path(base_workbook)
        if not self.base_workbook.is_file():
            raise FileNotFoundError(self.base_workbook)

    def write(
        self,
        output_path: str | Path,
        rows: Iterable[Mapping],
        *,
        collector_name: str = "",
        receiver_name: str = "",
        handover_at: datetime | None = None,
        pdf_path: str | Path | None = None,
    ) -> Path:
        if platform.system().lower() != "windows":
            raise RuntimeError("Η τελική δημιουργία Πρωτοκόλλου Excel απαιτεί Windows/Excel.")
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:
            raise RuntimeError("Λείπει η υποστήριξη Excel από το Windows build.") from exc

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pdf = Path(pdf_path) if pdf_path else None
        if pdf is not None:
            pdf.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(output.suffix + ".tmp.xlsx")
        tmp.unlink(missing_ok=True)
        shutil.copy2(self.base_workbook, tmp)

        data = list(rows)
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
            wb = excel.Workbooks.Open(Filename=str(tmp), UpdateLinks=False, ReadOnly=False, Notify=False)
            ws = wb.Worksheets("ΠΡΩΤΟΚΟΛΛΟ")
            first_row = 12
            base_last_data = 40
            base_summary = 41
            extra = max(0, len(data) - (base_last_data - first_row + 1))
            if extra:
                for i in range(1, int(ws.Shapes.Count) + 1):
                    try:
                        ws.Shapes.Item(i).Placement = 2
                    except Exception:
                        pass
                for _ in range(extra):
                    ws.Rows(base_summary).Insert(Shift=-4121, CopyOrigin=0)
            summary = base_summary + extra
            last_data_row = max(first_row, first_row + len(data) - 1)

            stamp = handover_at or datetime.now()
            collector = str(collector_name or "").strip()
            receiver = str(receiver_name or "").strip()
            collector_display = collector or "______________________________"
            receiver_display = receiver or "______________________________"
            weekday = _GREEK_WEEKDAYS.get(stamp.weekday(), "")
            ws.Range("A5").Value = (
                f"Στην Κρυσταλλοπηγή σήμερα την {stamp:%d/%m/%Y} ημέρα {weekday} και ώρα {stamp:%H:%M}, "
                f"εγώ ο {collector_display} παρέδωσα στον {receiver_display} τις παρακάτω δεσμεύσεις "
                "διοικητικών προστίμων e-paravolo, Διπλότυπα και χρηματικά ποσά:"
            )
            try:
                ws.Range("A5:F10").WrapText = True
                ws.Range("A5:F10").HorizontalAlignment = -4131
                ws.Range("A5:F10").VerticalAlignment = -4160
            except Exception:
                pass
            collector_sig = f"Ο ΠΑΡΑΔΟΥΣ\n{collector}".rstrip()
            receiver_sig = f"Ο ΠΑΡΑΛΑΒΩΝ\n{receiver}".rstrip()
            if collector and receiver:
                stamp_text = stamp.strftime("%d/%m/%Y %H:%M")
                collector_sig += f"\nΗλεκτρονική καταχώριση παράδοσης: {stamp_text}"
                receiver_sig += f"\nΗλεκτρονική καταχώριση παραλαβής: {stamp_text}"
            _set_shape_text(ws, "TextBox 3", collector_sig)
            _set_shape_text(ws, "TextBox 5", receiver_sig)

            ws.Range(f"A{first_row}:F{summary-1}").ClearContents()
            for idx, row in enumerate(data, start=1):
                r = first_row + idx - 1
                method = str(row.get("payment_type") or "").strip() or "EISPRAXI"
                ws.Cells(r, 1).Value = idx
                ws.Cells(r, 2).Value = str(row.get("protocol_no") or "")
                ws.Cells(r, 3).Value = float(row.get("amount") or 0)
                ws.Cells(r, 4).Value = method
                ws.Cells(r, 5).Value = str(row.get("measure") or "")
                ws.Cells(r, 6).Value = str(row.get("paravolo") or "")

            formula_last = max(first_row, last_data_row)
            ws.Cells(summary, 2).Value = "ΣΥΝ ΧΡΗΜ ΠΟΣΟ"
            ws.Cells(summary + 1, 2).Value = "ΣΥΝ Eparavolo"
            ws.Cells(summary + 2, 2).Value = "ΣΥΝ ΕΦΟΡΙΑ"
            formulas, unknown = protocol_category_formulas(data, first_row)
            ws.Cells(summary + 3, 2).Value = (
                "ΓΕΝ ΣΥΝΟΛΟ (με μη ταξινομημένες εξοφλήσεις)" if unknown else "ΓΕΝ ΣΥΝΟΛΟ"
            )
            ws.Cells(summary, 3).Formula = formulas["payment"]
            ws.Cells(summary + 1, 3).Formula = formulas["eparavolo"]
            ws.Cells(summary + 2, 3).Formula = formulas["detypa"]
            ws.Cells(summary + 3, 3).Formula = f'=SUM(C{first_row}:C{formula_last})'

            try:
                ws.PageSetup.PrintArea = "$A$1:$F$" + str(summary + 13)
                ws.PageSetup.Orientation = 1
                ws.PageSetup.Zoom = False
                ws.PageSetup.FitToPagesWide = 1
                ws.PageSetup.FitToPagesTall = False
            except Exception:
                pass

            ws.Calculate()
            wb.Save()
            if pdf is not None:
                pdf.unlink(missing_ok=True)
                ws.ExportAsFixedFormat(0, str(pdf))
            wb.Close(SaveChanges=False); wb = None
            if output.exists():
                output.unlink()
            tmp.replace(output)
            return output
        finally:
            if wb is not None:
                try:
                    wb.Close(SaveChanges=False)
                except Exception:
                    pass
            if excel is not None:
                try:
                    excel.Quit()
                except Exception:
                    pass
            try:
                pythoncom.CoUninitialize()  # type: ignore[name-defined]
            except Exception:
                pass
            if tmp.exists() and tmp != output:
                tmp.unlink(missing_ok=True)


class TestProtocolWorkbookWriter:
    def write(
        self,
        output_path: str | Path,
        rows: Iterable[Mapping],
        *,
        collector_name: str = "",
        receiver_name: str = "",
        handover_at: datetime | None = None,
        pdf_path: str | Path | None = None,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        data = list(rows)
        stamp = (handover_at or datetime.now()).isoformat(timespec="minutes")
        prefix = "TEST_XLSX\n"
        if collector_name or receiver_name:
            prefix += f"collector={collector_name}\nreceiver={receiver_name}\nhandover={stamp}\n"
        output.write_text(
            prefix + "\n".join(str(dict(x)) for x in data),
            encoding="utf-8",
        )
        if pdf_path:
            pdf = Path(pdf_path)
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_text(
                "TEST_PDF\n"
                f"collector={collector_name}\nreceiver={receiver_name}\nhandover={stamp}\n",
                encoding="utf-8",
            )
        return output
