"""Deterministically reproduce the Windows delete-pending acquisition race."""
from pathlib import Path
import pytest
from app.core.lock import SharedWriteLock


def denied():
    error=PermissionError('synthetic Windows delete-pending')
    error.winerror=5
    return error


def test_winerror5_after_other_writer_removes_lock_retries_only_atomic_acquisition(tmp_path,monkeypatch):
    original=Path.mkdir
    lock=SharedWriteLock(tmp_path,timeout=2)
    attempts=[]
    def race(path,*args,**kw):
        if path==lock.lock_dir:
            attempts.append(path)
            if len(attempts)==1:
                # Windows mkdir reports ERROR_ACCESS_DENIED for delete-pending;
                # another writer completes rmdir before our exists() check.
                assert not path.exists()
                raise denied()
        return original(path,*args,**kw)
    monkeypatch.setattr(Path,'mkdir',race)
    with lock.acquire():
        assert len(attempts)==2
        assert (lock.lock_dir/'owner.json').is_file()
    assert not lock.lock_dir.exists()


def test_persistent_windows_permission_denial_is_bounded_and_does_not_enter(tmp_path,monkeypatch):
    original=Path.mkdir
    lock=SharedWriteLock(tmp_path,timeout=0)
    def no_access(path,*args,**kw):
        if path==lock.lock_dir:raise denied()
        return original(path,*args,**kw)
    monkeypatch.setattr(Path,'mkdir',no_access)
    with pytest.raises(PermissionError):
        with lock.acquire():pytest.fail('must not enter without successful mkdir')
    assert not lock.lock_dir.exists()


def test_existing_foreign_owner_is_never_removed_on_windows_permission_error(tmp_path,monkeypatch):
    lock=SharedWriteLock(tmp_path,timeout=0)
    lock.lock_dir.mkdir();owner=lock.lock_dir/'owner.json';owner.write_bytes(b'FOREIGN OWNER')
    original=Path.mkdir
    def occupied(path,*args,**kw):
        if path==lock.lock_dir:raise denied()
        return original(path,*args,**kw)
    monkeypatch.setattr(Path,'mkdir',occupied)
    with pytest.raises(TimeoutError):
        with lock.acquire():pytest.fail('must not acquire a foreign lock')
    assert owner.read_bytes()==b'FOREIGN OWNER'


def test_other_permission_errors_are_not_reclassified_as_windows_contention(tmp_path,monkeypatch):
    lock=SharedWriteLock(tmp_path,timeout=30)
    original=Path.mkdir
    def forbidden(path,*args,**kw):
        if path==lock.lock_dir:raise PermissionError('real ACL denial')
        return original(path,*args,**kw)
    monkeypatch.setattr(Path,'mkdir',forbidden)
    with pytest.raises(PermissionError,match='real ACL denial'):
        with lock.acquire():pytest.fail('no permissions')


def test_windows_comparison_only_accepts_the_exact_recorded_baseline_race_and_never_current_failures(monkeypatch):
    import importlib.util
    tools=Path(__file__).resolve().parents[2]/'tools'
    monkeypatch.syspath_prepend(str(tools))
    from compare_field_regressions import compare_field,LOCK_TEST
    baseline={LOCK_TEST:'failure','original':'passed'}
    current={LOCK_TEST:'passed','original':'passed','new':'passed'}
    signature='PermissionError [WinError 5] .write.lock self.lock_dir.mkdir()'
    result=compare_field(baseline,current,signature)
    assert result['compatible'] and result['historical_failures']==[LOCK_TEST]
    assert result['changed_outcomes'][LOCK_TEST]==['failure','passed']
    assert not compare_field(baseline,current,'SQLite corruption')['compatible']
    assert not compare_field(baseline,current|{'original':'failure'},signature)['compatible']
    assert not compare_field(baseline,current|{'new':'skipped'},signature)['compatible']
    assert not compare_field(baseline,current|{LOCK_TEST:'failure'},signature)['compatible']
    assert not compare_field(baseline,{'original':'passed'},signature)['compatible']
    assert not compare_field(baseline|{'other':'failure'},current|{'other':'passed'},signature)['compatible']
    assert compare_field(current,current)['compatible']
