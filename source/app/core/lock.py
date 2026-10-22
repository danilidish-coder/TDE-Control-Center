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
                try:
                    (self.lock_dir / "owner.json").write_text(json.dumps(meta), encoding="utf-8")
                except OSError:
                    # This directory was created by this acquisition, which has
                    # not yet entered the protected write operation.
                    (self.lock_dir / "owner.json").unlink(missing_ok=True)
                    self.lock_dir.rmdir()
                    raise
                break
            except FileExistsError:
                self._wait_for_lock(started)
            except PermissionError as exc:
                # On Windows (and occasionally SMB), attempting to create a lock
                # directory that another process owns may surface as WinError 5
                # instead of FileExistsError. Treat it as contention only when
                # the lock path actually exists; otherwise preserve the real
                # permission failure.
                if not self.lock_dir.exists():
                    # Windows may report delete-pending as WinError 5, then
                    # the other writer finishes rmdir before this exists check.
                    # Retry mkdir within the original timeout; never enter the
                    # critical section without acquiring a new owned directory.
                    if getattr(exc, "winerror", None) == 5 and time.monotonic() - started < self.timeout:
                        time.sleep(0.15)
                        continue
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
        if time.monotonic() - started >= self.timeout:
            message = "Η βάση χρησιμοποιείται από άλλο σταθμό. Δοκιμάστε ξανά."
            try:
                age = time.time() - self.lock_dir.stat().st_mtime
            except FileNotFoundError:
                return
            if age > self.stale_after:
                message += (
                    " Το παλιό κλείδωμα δεν αφαιρέθηκε αυτόματα, διότι η ηλικία του "
                    "δεν αποδεικνύει ότι ο ιδιοκτήτης έχει τερματίσει. Απαιτείται έλεγχος "
                    "και επιβεβαίωση διαχειριστή ότι όλοι οι σταθμοί έχουν σταματήσει "
                    "να γράφουν πριν από χειροκίνητη αποκατάσταση."
                )
            raise TimeoutError(message)
        time.sleep(0.15)
