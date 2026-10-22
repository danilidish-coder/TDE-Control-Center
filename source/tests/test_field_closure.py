from datetime import datetime
from openpyxl import load_workbook
from test_phase2_shift_times import seed,text
from app.core.db import Database
from app.features.fines.service import FineService
from app.features.refusals.service import RefusalService
from app.features.daily_activity.service import DailyActivityService


def test_all_new_closed_shift_reports_use_neutral_closure_and_preserve_identity_times(tmp_path,monkeypatch):
    import app.core.paths as paths
    monkeypatch.setattr(paths,'runtime_root',lambda:tmp_path)
    db=Database(tmp_path/'test.sqlite3')
    sid=seed(db,datetime(2026,12,31,23,47))
    db.close_shift(datetime(2027,1,1,2,13))
    fines=text(FineService(db).generate_shift_report(sid,archive=True))
    vas=text(RefusalService(db).generate_vas(sid,archive=True))
    book=load_workbook(DailyActivityService(db).generate(sid,archive=True))
    daily=' '.join(str(c.value or '') for row in book.active for c in row)
    book.close()
    for content in (fines,vas,daily):
        assert 'Η εφαρμογή έκλεισε' in content
        assert 'υπογράφηκε ηλεκτρονικά' not in content.lower()
        assert 'SYNTHETIC OFFICER' in content
        assert '23:47' in content and '02:13' in content
    # Preserve a pre-existing historical document byte-for-byte.
    historical=tmp_path/'old.docx'
    historical.write_bytes(b'HISTORICAL DO NOT REWRITE')
    FineService(db).generate_shift_report(sid)
    assert historical.read_bytes()==b'HISTORICAL DO NOT REWRITE'
