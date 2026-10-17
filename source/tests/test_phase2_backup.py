from contextlib import closing
import shutil
import sqlite3

import pytest

from app.infrastructure.backup import backup_database


def test_backup_includes_committed_wal_pages_that_file_copy_loses(tmp_path, monkeypatch):
    import app.infrastructure.backup as module
    folder = tmp_path / 'backups'
    monkeypatch.setattr(module, 'backup_root', lambda: folder)
    db = tmp_path / 'source.sqlite3'
    with closing(sqlite3.connect(db)) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA wal_autocheckpoint=0')
        connection.execute('CREATE TABLE data(value TEXT)')
        connection.execute("INSERT INTO data VALUES('committed synthetic')")
        connection.commit()
        copy = tmp_path / 'copy.sqlite3'
        shutil.copy2(db, copy)
        with closing(sqlite3.connect(copy)) as copied:
            with pytest.raises(sqlite3.OperationalError, match='no such table'):
                copied.execute('SELECT * FROM data').fetchall()
        result = backup_database(db)
        with closing(sqlite3.connect(result)) as backup:
            assert backup.execute('SELECT * FROM data').fetchall() == [('committed synthetic',)]
            assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert backup.execute('PRAGMA foreign_key_check').fetchall() == []


def test_backups_are_distinct_in_same_instant_and_retain_thirty(tmp_path, monkeypatch):
    import app.infrastructure.backup as module
    from datetime import datetime
    class Clock(datetime):
        @classmethod
        def now(cls): return cls(2026, 10, 17, 2, 13, 1)
    monkeypatch.setattr(module, 'datetime', Clock)
    folder = tmp_path / 'backups'
    monkeypatch.setattr(module, 'backup_root', lambda: folder)
    db = tmp_path / 'source.sqlite3'
    with closing(sqlite3.connect(db)) as connection:
        connection.execute('CREATE TABLE data(value INTEGER)')
        connection.commit()
    results = [backup_database(db) for _ in range(32)]
    assert len(set(results)) == 32
    assert len(list(folder.glob('tde_*.sqlite3'))) == 30
    assert not list(folder.glob('.*'))


def test_backup_failure_preserves_previous_backups_and_cleans_partial(tmp_path, monkeypatch):
    import app.infrastructure.backup as module
    folder = tmp_path / 'backups'
    monkeypatch.setattr(module, 'backup_root', lambda: folder)
    db = tmp_path / 'source.sqlite3'
    with closing(sqlite3.connect(db)) as connection:
        connection.execute('CREATE TABLE data(value INTEGER)')
        connection.commit()
    valid = backup_database(db)
    previous = valid.read_bytes()
    db.write_bytes(b'not a database')
    with pytest.raises(sqlite3.DatabaseError):
        backup_database(db)
    assert valid.read_bytes() == previous
    assert list(folder.iterdir()) == [valid]
    assert backup_database(tmp_path / 'missing.sqlite3') is None


def test_backup_encodes_unc_filename_without_nonlocal_uri_authority(tmp_path, monkeypatch):
    from pathlib import PureWindowsPath
    import app.infrastructure.backup as module
    class Source:
        def exists(self): return True
        def resolve(self): return PureWindowsPath('//SYNTHETIC-SERVER/share/a b.sqlite3')
    monkeypatch.setattr(module, 'backup_root', lambda: tmp_path / 'backup')
    calls = []
    def capture(filename, **kwargs):
        calls.append((filename, kwargs))
        raise OSError('synthetic connection stop')
    monkeypatch.setattr(module.sqlite3, 'connect', capture)
    with pytest.raises(OSError, match='synthetic connection stop'):
        backup_database(Source())
    assert calls == [('file:////SYNTHETIC-SERVER/share/a%20b.sqlite3?mode=ro', {'uri': True})]
    assert list((tmp_path / 'backup').iterdir()) == []
