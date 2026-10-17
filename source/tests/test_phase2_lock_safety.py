import json
import os
import socket
import time

import pytest

from app.core.lock import SharedWriteLock


@pytest.mark.parametrize('owner', [
    {'host': socket.gethostname(), 'pid': os.getpid()},
    {'host': 'SYNTHETIC-REMOTE-SMB', 'pid': 999999},
    {'host': socket.gethostname(), 'pid': 999999},
    None,
])
def test_old_lock_is_never_stolen_by_age_even_with_unknown_or_dead_owner(tmp_path, owner):
    lock = SharedWriteLock(tmp_path, timeout=0, stale_after=1)
    lock.lock_dir.mkdir()
    if owner is not None:
        (lock.lock_dir / 'owner.json').write_text(json.dumps(owner))
    before = {p.name: p.read_bytes() for p in lock.lock_dir.iterdir()}
    os.utime(lock.lock_dir, (time.time() - 1000, time.time() - 1000))
    with pytest.raises(TimeoutError, match='επιβεβαίωση διαχειριστή'):
        with lock.acquire():
            pytest.fail('must not enter another owner’s critical section')
    assert lock.lock_dir.exists()
    assert {p.name: p.read_bytes() for p in lock.lock_dir.iterdir()} == before


def test_exception_releases_own_lock_and_next_write_can_enter(tmp_path):
    lock = SharedWriteLock(tmp_path, timeout=0)
    with pytest.raises(ValueError, match='write failed'):
        with lock.acquire():
            raise ValueError('write failed')
    assert not lock.lock_dir.exists()
    with lock.acquire():
        assert (lock.lock_dir / 'owner.json').exists()
    assert not lock.lock_dir.exists()


def test_owner_metadata_failure_does_not_leave_orphan_lock(tmp_path, monkeypatch):
    from pathlib import Path
    original = Path.write_text
    def fail(path, *args, **kwargs):
        if path.name == 'owner.json':
            raise OSError('disk full')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', fail)
    lock = SharedWriteLock(tmp_path)
    with pytest.raises(OSError, match='disk full'):
        with lock.acquire():
            pytest.fail('metadata did not persist')
    assert not lock.lock_dir.exists()
