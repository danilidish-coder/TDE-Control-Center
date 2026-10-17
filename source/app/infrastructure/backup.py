from __future__ import annotations

from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.core.paths import backup_root
from app.infrastructure.atomic_output import atomic_output


def backup_database(db_file: Path) -> Path | None:
    if not db_file.exists():
        return None
    folder = backup_root()
    dest = folder / f"tde_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid4().hex[:8]}.sqlite3"
    # SQLite's backup API includes committed WAL pages and gives a consistent
    # snapshot while other connections write. A file copy cannot do that.
    with atomic_output(dest) as temporary:
        with closing(sqlite3.connect(db_file.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(temporary)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError("Το αντίγραφο ασφαλείας απέτυχε στον έλεγχο ακεραιότητας.")
    backups = sorted(folder.glob("tde_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[30:]:
        old.unlink(missing_ok=True)
    return dest
