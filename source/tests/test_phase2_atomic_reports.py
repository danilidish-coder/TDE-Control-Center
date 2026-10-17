from datetime import datetime, timedelta
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
import pytest

from app.core.db import Database
from app.features.daily_activity.service import DailyActivityService
from app.features.fines.documents import FineEntry
from app.features.fines.service import FineService
from app.infrastructure.atomic_output import atomic_output
from app.shared.documents.docx_mirror import _pack


def test_docx_failed_zip_write_preserves_previous_valid_document(tmp_path, monkeypatch):
    source = tmp_path / 'parts'
    source.mkdir()
    (source / 'document.xml').write_text('previous')
    output = tmp_path / 'report.docx'
    _pack(source, output)
    previous = output.read_bytes()
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(ZipFile, 'write', fail)
    with pytest.raises(OSError, match='disk full'):
        _pack(source, output)
    assert output.read_bytes() == previous
    with ZipFile(output) as package:
        assert package.read('document.xml') == b'previous'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['parts', 'report.docx']


def test_locked_target_preserves_old_report_and_cleans_only_owned_temporary(tmp_path, monkeypatch):
    import app.infrastructure.atomic_output as module
    output = tmp_path / 'report.docx'
    output.write_bytes(b'previous')
    unrelated = tmp_path / '.someone-else.docx'
    unrelated.write_bytes(b'keep')
    def denied(*args):
        raise PermissionError('Word lock')
    monkeypatch.setattr(module.os, 'replace', denied)
    with pytest.raises(PermissionError, match='Word lock'):
        with atomic_output(output) as temporary:
            assert temporary.parent == output.parent
            temporary.write_bytes(b'new')
    assert output.read_bytes() == b'previous'
    assert unrelated.read_bytes() == b'keep'
    assert len(list(tmp_path.iterdir())) == 2


def test_daily_failed_save_preserves_valid_xlsx_and_database(tmp_path, monkeypatch):
    import app.core.paths as paths
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    db = Database(tmp_path / 'test.sqlite3')
    start = datetime(2026, 10, 17, 2, 13)
    sid = db.start_shift('SYNTHETIC', start)
    daily = DailyActivityService(db)
    output = daily.generate(sid, end_dt=start + timedelta(hours=1))
    previous = output.read_bytes()
    row = dict(db.get_shift(sid))
    def fail(self, filename):
        filename.write_bytes(b'partial zip')
        raise OSError('disk full')
    monkeypatch.setattr(Workbook, 'save', fail)
    with pytest.raises(OSError, match='disk full'):
        daily.generate(sid, end_dt=start + timedelta(hours=2))
    assert output.read_bytes() == previous
    assert dict(db.get_shift(sid)) == row
    book = load_workbook(output)
    assert start.strftime('%d/%m/%Y %H:%M') in book.active['A7'].value
    book.close()
    assert list(output.parent.glob('.*.xlsx')) == []


def test_fines_header_failure_leaves_no_temporary_and_keeps_valid_report(tmp_path, monkeypatch):
    import app.core.paths as paths
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    db = Database(tmp_path / 'test.sqlite3')
    start = datetime(2026, 10, 17, 2, 13)
    sid = db.start_shift('SYNTHETIC', start)
    service = FineService(db)
    service.add_fine('IMPOSITION', FineEntry(date='17/10/2026', surname='SYNTHETIC', amount=600), start)
    output = service.generate_shift_report(sid, end_dt=start + timedelta(hours=1))
    previous = output.read_bytes()
    def fail(path, **kwargs):
        path.write_bytes(b'partial')
        raise OSError('header failure')
    monkeypatch.setattr(service.engine, 'create_report_window', fail)
    with pytest.raises(OSError, match='header failure'):
        service.generate_shift_report(sid, end_dt=start + timedelta(hours=2))
    assert output.read_bytes() == previous
    assert not output.with_suffix('.header.docx').exists()
    assert not db.lock.lock_dir.exists()
