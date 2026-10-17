from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import pytest
import app.infrastructure.word_open as module


def valid_docx(path):
    with ZipFile(path, 'w') as package:
        package.writestr('[Content_Types].xml', '<Types/>')
        package.writestr('word/document.xml', '<document/>')
    return path


def test_repeated_word_open_uses_distinct_copies_and_explicit_executable(tmp_path, monkeypatch):
    source = valid_docx(tmp_path / 'report.docx')
    original = source.read_bytes()
    calls = []
    word = tmp_path / 'Program Files' / 'WINWORD.EXE'
    monkeypatch.setattr(module, 'find_word_executable', lambda: word)
    monkeypatch.setattr(module, 'preview_root', lambda: tmp_path / 'preview')
    monkeypatch.setattr(module.subprocess, 'Popen', lambda args: calls.append(args))
    first, second = module.open_word_document(source), module.open_word_document(source)
    assert first != second and first != source and second != source
    assert calls == [[str(word), str(first)], [str(word), str(second)]]
    assert first.read_bytes() == second.read_bytes() == source.read_bytes() == original
    assert not source.with_suffix('.pdf').exists()


def test_missing_word_reports_launch_problem_and_retains_docx(tmp_path, monkeypatch):
    source = valid_docx(tmp_path / 'report.docx')
    monkeypatch.setattr(module, 'find_word_executable', lambda: None)
    with pytest.raises(FileNotFoundError, match='DOCX δημιουργήθηκε και είναι έγκυρο'):
        module.open_word_document(source)
    assert source.exists() and not source.with_suffix('.pdf').exists()


@pytest.mark.parametrize('problem', ['launch', 'copy', 'directory'])
def test_word_open_failure_preserves_source_and_cleans_partial_copy(tmp_path, monkeypatch, problem):
    source = valid_docx(tmp_path / 'report.docx')
    original = source.read_bytes()
    monkeypatch.setattr(module, 'find_word_executable', lambda: Path('WINWORD.EXE'))
    preview = tmp_path / 'preview'
    monkeypatch.setattr(module, 'preview_root', lambda: preview)
    def fail(*args, **kwargs): raise PermissionError('synthetic access denied')
    if problem == 'launch': monkeypatch.setattr(module.subprocess, 'Popen', fail)
    elif problem == 'copy': monkeypatch.setattr(module.shutil, 'copyfile', fail)
    else: preview.write_text('cannot create folder here')
    with pytest.raises(OSError, match='Απέτυχε το άνοιγμα'):
        module.open_word_document(source)
    assert source.read_bytes() == original
    assert not list(tmp_path.rglob('report_*.docx'))


def test_invalid_and_missing_docx_are_distinct_from_launch_failure(tmp_path, monkeypatch):
    def must_not_launch(): pytest.fail('validate before looking for Word')
    monkeypatch.setattr(module, 'find_word_executable', must_not_launch)
    with pytest.raises(FileNotFoundError, match='Δεν βρέθηκε'):
        module.open_word_document(tmp_path / 'missing.docx')
    source = tmp_path / 'broken.docx'
    source.write_bytes(b'truncated zip')
    with pytest.raises(ValueError, match='δεν είναι έγκυρο DOCX'):
        module.open_word_document(source)


def test_word_registry_lookup_supports_32_and_64_bit_office(tmp_path, monkeypatch):
    import sys
    word = tmp_path / 'Office' / 'WINWORD.EXE'
    word.parent.mkdir(); word.touch()
    calls = []
    class Key:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def open_key(hive, key, reserved, flags):
        calls.append((hive, key, flags))
        if hive == 2 and flags == 33: return Key()
        raise FileNotFoundError('not installed in this view')
    registry = SimpleNamespace(HKEY_CURRENT_USER=1, HKEY_LOCAL_MACHINE=2, KEY_READ=1, KEY_WOW64_64KEY=64, KEY_WOW64_32KEY=32, OpenKey=open_key, QueryValueEx=lambda key, name: (f'"{word}"', 1))
    monkeypatch.setitem(sys.modules, 'winreg', registry)
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    assert module.find_word_executable() == word
    assert any(flags == 65 for _, _, flags in calls) and any(flags == 33 for _, _, flags in calls)


def test_all_fines_ui_routes_use_word_and_report_generation_failure(tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QTableWidgetItem, QMessageBox
    import app.core.paths as paths
    import app.features.fines.page as page_module
    import app.features.fines.archive as archive_module
    import app.features.reports.page as reports_module
    from app.core.db import Database
    from app.features.fines.service import FineService
    from app.features.refusals.service import RefusalService
    from app.features.daily_activity.service import DailyActivityService
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / 'test.sqlite3'); db.start_shift('SYNTHETIC')
    source = valid_docx(tmp_path / 'report.docx')
    service = FineService(db)
    monkeypatch.setattr(service, 'generate_shift_report', lambda *args, **kwargs: source)
    calls, warnings = [], []
    monkeypatch.setattr(QMessageBox, 'warning', lambda parent, title, message: warnings.append(message))
    for target in (page_module, archive_module, reports_module):
        monkeypatch.setattr(target, 'os', SimpleNamespace(name='nt'))
        monkeypatch.setattr(target, 'open_word_document', lambda path: calls.append(path))
    page = page_module.FinesPage(service)
    archive = archive_module.FinesArchiveDialog(service)
    reports = reports_module.ShiftReportsPage(db, service, RefusalService(db), DailyActivityService(db))
    try:
        page.preview_report()
        for widget, data in ((archive, (1, 1)), (reports, (1, 'FINES'))):
            widget.table.setRowCount(1)
            item = QTableWidgetItem('synthetic'); item.setData(Qt.UserRole, data)
            widget.table.setItem(0, 0, item); widget.table.selectRow(0)
        archive.preview_selected_shift(); reports.open_selected()
        assert calls == [source, source, source] and not warnings
        def generation_failed(*args, **kwargs): raise OSError('synthetic DOCX generation failure')
        monkeypatch.setattr(service, 'generate_shift_report', generation_failed)
        page.preview_report()
        assert warnings == ['synthetic DOCX generation failure'] and len(calls) == 3
    finally:
        page.close(); archive.close(); reports.close()
