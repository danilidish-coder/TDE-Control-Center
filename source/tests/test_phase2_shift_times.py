from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from openpyxl import load_workbook
import pytest

from app.core.db import Database
from app.features.fines.documents import FineEntry, FineReportEngine
from app.features.fines.service import FineService
from app.features.refusals.documents import RefusalEntry
from app.features.refusals.service import RefusalService
from app.features.daily_activity.service import DailyActivityService


def text(path):
    with ZipFile(path) as package:
        root = etree.fromstring(package.read('word/document.xml'))
    return ''.join(root.xpath('//*[local-name()="t"]/text()'))


def seed(db, start):
    sid = db.start_shift('SYNTHETIC OFFICER', start, officer_agms='999999', officer_rank_full='TEST')
    FineService(db).add_fine('IMPOSITION', FineEntry(date=start.strftime('%d/%m/%Y'), surname='SYNTHETIC', amount=600), start)
    RefusalService(db).add_refusal(RefusalEntry(aa='1', year=str(start.year), protocol_prefix='456', protocol_no='1', date=start.strftime('%d-%m-%Y'), time=start.strftime('%H:%M'), sex='M', surname='SYNTHETIC', name='TEST', birth_date='01-01-1990', passport='TEST', issue_date='01-01-2025', reason='A-ΕΛΛΕΙΨΗ ΕΓΚΥΡΟΥ ΤΑΞ. ΕΓΓΡΑΦΟΥ', language='ΑΓΓΛΙΚΑ'), start)
    return sid


def capture(db, sid, *, end_dt=None, archive=False):
    fines = FineService(db).generate_shift_report(sid, end_dt=end_dt, archive=archive)
    vas = RefusalService(db).generate_vas(sid, end_dt=end_dt, archive=archive)
    daily = DailyActivityService(db).generate(sid, end_dt=end_dt, archive=archive)
    book = load_workbook(daily)
    sheet = book['Ημερήσια Δραστηριότητα']
    result = (text(fines), text(vas), sheet['A7'].value, sheet['C50'].value)
    book.close()
    return result


@pytest.mark.parametrize('start,duration', [
    (datetime(2026, 10, 17, 3, 17, 25), timedelta(minutes=27)),
    (datetime(2026, 10, 17, 23, 43), timedelta(hours=3, minutes=12)),
    (datetime(2026, 12, 31, 22, 49), timedelta(hours=29, minutes=6)),
    (datetime(2026, 10, 17, 7, 13), timedelta(hours=8, minutes=37)),
    (datetime(2026, 10, 17, 12, 21, 1), timedelta(0)),
])
def test_all_reports_use_stored_window_after_restart_and_later_reopen(tmp_path, monkeypatch, start, duration):
    import app.core.paths as paths
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    db = Database(tmp_path / 'shift.sqlite3')
    sid = seed(db, start)
    end = start + duration
    db.close_shift(end)
    original = dict(db.get_shift(sid))
    restarted = Database(db.path)
    before = capture(restarted, sid, archive=True)
    after = capture(Database(db.path), sid, end_dt=end + timedelta(days=365), archive=True)
    assert before == after
    assert dict(restarted.get_shift(sid)) == original
    fines, vas, daily, signature = after
    for stamp in (start, end):
        assert stamp.strftime('%d/%m/%Y') in fines
        assert stamp.strftime('%H:%M') in fines and stamp.strftime('%H:%M') in vas
        assert stamp.strftime('%d-%m-%Y').lstrip('0') in vas
        assert stamp.strftime('%d/%m/%Y %H:%M') in daily
    assert end.strftime('%d/%m/%Y %H:%M') in signature
    assert all('ΕΝΕΡΓΗ ΒΑΡΔΙΑ' not in item for item in after)


def test_active_previews_advance_current_end_without_changing_recorded_start(tmp_path, monkeypatch):
    import app.core.paths as paths
    import app.features.fines.service as fines_module
    import app.features.refusals.service as refusals_module
    import app.features.daily_activity.service as daily_module
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    start = datetime(2026, 10, 17, 23, 37)
    class Clock(datetime):
        current = start + timedelta(minutes=31)
        @classmethod
        def now(cls, tz=None): return cls.current
    for module in (fines_module, refusals_module, daily_module):
        monkeypatch.setattr(module, 'datetime', Clock)
    db = Database(tmp_path / 'active.sqlite3')
    sid = seed(db, start)
    first = capture(db, sid)
    Clock.current += timedelta(minutes=47)
    second = capture(Database(db.path), sid)
    for result in (first, second):
        assert 'ΕΝΕΡΓΗ ΒΑΡΔΙΑ' in result[0] and 'ΕΝΕΡΓΗ ΒΑΡΔΙΑ' in result[1] and 'ΕΝΕΡΓΗ ΒΑΡΔΙΑ' in result[3]
        assert 'προσωρινή λήξη' in result[0] and 'προσωρινή λήξη' in result[1] and 'προσωρινή λήξη' in result[3]
        assert start.strftime('%H:%M') in result[0] and start.strftime('%H:%M') in result[1]
    assert Clock.current.strftime('%H:%M') in second[0] and Clock.current.strftime('%H:%M') in second[1]
    assert first != second
    assert db.get_shift(sid)['started_at'] == start.isoformat(timespec='seconds')
    assert db.get_shift(sid)['ended_at'] is None


def test_database_records_actual_clock_without_duration_defaults(tmp_path, monkeypatch):
    import app.core.db as module
    class Clock(datetime):
        current = datetime(2026, 10, 17, 2, 19, 37)
        @classmethod
        def now(cls, tz=None): return cls.current
    monkeypatch.setattr(module, 'datetime', Clock)
    db = Database(tmp_path / 'clock.sqlite3')
    sid = db.start_shift('SYNTHETIC')
    start = Clock.current
    Clock.current += timedelta(hours=37, minutes=13)
    db.close_shift()
    assert db.get_shift(sid)['started_at'] == start.isoformat(timespec='seconds')
    assert db.get_shift(sid)['ended_at'] == Clock.current.isoformat(timespec='seconds')


def test_legacy_fines_entry_does_not_invent_a_day_window(tmp_path):
    from app.core.paths import resource_path
    engine = FineReportEngine(resource_path('Anafora_base.docx'))
    with pytest.raises(ValueError, match='πραγματικές ώρες'):
        engine.create_report(tmp_path / 'not-created.docx', officer_name='SYNTHETIC', officer_agms='', operational_day=datetime(2026, 10, 17).date())
    assert not (tmp_path / 'not-created.docx').exists()
