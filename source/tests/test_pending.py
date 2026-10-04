from datetime import datetime

from app.core.db import Database
from app.services.pending import DAILY_ACTIVITY, FINES_REPORT, REFUSALS_VAS, PendingService


class FakeGenerator:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def generate_shift_report(self, shift_id, archive=False):
        self.calls.append((shift_id, archive))
        if self.fail:
            raise RuntimeError("fine archive locked")
        return "fine-ok"

    def generate_vas(self, shift_id, archive=False):
        self.calls.append((shift_id, archive))
        if self.fail:
            raise RuntimeError("vas archive locked")
        return "vas-ok"

    def generate(self, shift_id, archive=False):
        self.calls.append((shift_id, archive))
        if self.fail:
            raise RuntimeError("daily archive locked")
        return "daily-ok"


def _closed_shift(db):
    sid = db.start_shift("ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ", datetime(2026, 9, 25, 10, 0, 0))
    db.close_shift(datetime(2026, 9, 25, 20, 0, 0))
    return sid


def test_pending_is_created_only_for_real_failed_archive_and_other_jobs_continue(tmp_path):
    db = Database(tmp_path / "pending.sqlite3")
    sid = _closed_shift(db)
    fines = FakeGenerator(fail=True)
    vas = FakeGenerator(fail=False)
    daily = FakeGenerator(fail=False)
    service = PendingService(db, fines, vas, daily)

    result = service.archive_shift(sid)

    assert result.completed == [REFUSALS_VAS, DAILY_ACTIVITY]
    assert [x[0] for x in result.failed] == [FINES_REPORT]
    assert db.pending_count() == 1
    row = db.list_pending_jobs()[0]
    assert row["shift_id"] == sid
    assert row["job_type"] == FINES_REPORT
    assert "locked" in row["last_error"]
    assert vas.calls == [(sid, True)] and daily.calls == [(sid, True)]


def test_retry_pending_resolves_exact_job_and_disables_pending_state(tmp_path):
    db = Database(tmp_path / "pending.sqlite3")
    sid = _closed_shift(db)
    fines = FakeGenerator(fail=True)
    service = PendingService(db, fines, FakeGenerator(), FakeGenerator())
    service.archive_shift(sid)
    assert service.count() == 1

    fines.fail = False
    result = service.retry_pending()

    assert result.failed == []
    assert result.completed == [FINES_REPORT]
    assert service.count() == 0
    assert db.list_pending_jobs() == []
    assert fines.calls == [(sid, True), (sid, True)]
