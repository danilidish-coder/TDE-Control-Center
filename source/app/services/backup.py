from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.core.paths import backup_root


def backup_database(db_file: Path) -> Path | None:
    if not db_file.exists():
        return None
    dest = backup_root() / f"tde_{datetime.now():%Y%m%d_%H%M%S}.sqlite3"
    shutil.copy2(db_file, dest)
    backups = sorted(backup_root().glob("tde_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[30:]:
        old.unlink(missing_ok=True)
    return dest
