from __future__ import annotations

import os
from pathlib import Path

from app.core.paths import resolve_runtime_path


def _export_excel(source: Path, target: Path) -> None:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore
    pythoncom.CoInitialize()
    excel = wb = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.ScreenUpdating = False
        wb = excel.Workbooks.Open(Filename=str(source), UpdateLinks=False, ReadOnly=True, Notify=False)
        wb.ExportAsFixedFormat(0, str(target))
        wb.Close(SaveChanges=False); wb = None
    finally:
        if wb is not None:
            try: wb.Close(SaveChanges=False)
            except Exception: pass
        if excel is not None:
            try: excel.Quit()
            except Exception: pass
        try: pythoncom.CoUninitialize()
        except Exception: pass


def _export_word(source: Path, target: Path) -> None:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore
    pythoncom.CoInitialize()
    word = doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False, Visible=False)
        doc.ExportAsFixedFormat(str(target), 17)
        doc.Close(False); doc = None
    finally:
        if doc is not None:
            try: doc.Close(False)
            except Exception: pass
        if word is not None:
            try: word.Quit()
            except Exception: pass
        try: pythoncom.CoUninitialize()
        except Exception: pass


def document_preview_path(path: str | Path) -> Path:
    source = resolve_runtime_path(path)
    if source.is_dir() or source.suffix.lower() == ".pdf":
        return source
    if source.suffix.lower() not in {".xlsx", ".xlsm", ".xls", ".docx", ".doc"}:
        return source
    target = source.with_suffix(".pdf")
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    target.unlink(missing_ok=True)
    if source.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        _export_excel(source, target)
    else:
        _export_word(source, target)
    return target if target.exists() else source


def open_document_preview(path: str | Path) -> Path:
    source = resolve_runtime_path(path)
    if os.name != "nt":
        return source
    try:
        target = document_preview_path(source)
    except Exception:
        target = source
    os.startfile(str(target))
    return target
