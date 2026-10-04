from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.core.db import Database


def test_serialized_concurrent_writes(tmp_path: Path):
    db_path = tmp_path / "concurrent.sqlite3"
    db = Database(db_path)
    person = db.get_or_create_person("TEST", "PERSON", "2000-01-01")

    def write_one(i):
        local = Database(db_path)
        return local.add_action(person, "TEST", reason=str(i))

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(write_one, range(60)))
    assert len(set(ids)) == 60
    assert len(db.person_history(person)) == 60
