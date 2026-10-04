from __future__ import annotations

import json
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path


class SharedWriteLock:
    """Application-level lock based on atomic directory creation.

    It is intentionally separate from SQLite locking so the storage backend can
    later be replaced if real SMB concurrency testing requires it.
    """

    def __init__(self, root: Path, timeout: float = 30.0, stale_after: float = 180.0):
        self.lock_dir = root / ".write.lock"
        self.timeout = timeout
        self.stale_after = stale_after

    @contextmanager
    def acquire(self):
        started = time.monotonic()
        while True:
            try:
                self.lock_dir.mkdir()
                meta = {
                    "pid": os.getpid(),
                    "host": socket.gethostname(),
                    "created": time.time(),
                }
                (self.lock_dir / "owner.json").write_text(json.dumps(meta), encoding="utf-8")
                break
            except FileExistsError:
                self._wait_for_lock(started)
            except PermissionError:
                # On Windows (and occasionally SMB), attempting to create a lock
                # directory that another process owns may surface as WinError 5
                # instead of FileExistsError. Treat it as contention only when
                # the lock path actually exists; otherwise preserve the real
                # permission failure.
                if not self.lock_dir.exists():
                    raise
                self._wait_for_lock(started)
        try:
            yield
        finally:
            try:
                for p in self.lock_dir.iterdir():
                    p.unlink(missing_ok=True)
                self.lock_dir.rmdir()
            except FileNotFoundError:
                pass

    def _wait_for_lock(self, started: float) -> None:
        self._clear_stale_lock()
        if time.monotonic() - started >= self.timeout:
            raise TimeoutError("Η βάση χρησιμοποιείται από άλλο σταθμό. Δοκιμάστε ξανά.")
        time.sleep(0.15)

    def _clear_stale_lock(self) -> None:
        try:
            age = time.time() - self.lock_dir.stat().st_mtime
            if age > self.stale_after:
                for p in self.lock_dir.iterdir():
                    p.unlink(missing_ok=True)
                self.lock_dir.rmdir()
        except FileNotFoundError:
            pass
        except PermissionError:
            # Another Windows/SMB client may be in the middle of releasing the
            # lock. It is safer to leave it alone and retry than to force it.
            pass
