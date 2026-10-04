from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterator

from .lock import SharedWriteLock
from .paths import db_path
from .textnorm import normalize_birth_date, normalize_text, phonetic_key

SCHEMA_VERSION = 7


class Database:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = SharedWriteLock(self.path.parent)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
        # WAL is deliberately avoided because this database may later be tested on SMB.
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute("PRAGMA synchronous=FULL")
        return con

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        with self.lock.acquire():
            con = self.connect()
            try:
                con.execute("BEGIN IMMEDIATE")
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

    @staticmethod
    def _columns(con: sqlite3.Connection, table: str) -> set[str]:
        return {str(r[1]) for r in con.execute(f"PRAGMA table_info({table})").fetchall()}

    def _init_schema(self) -> None:
        with self.write() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                officer_name TEXT NOT NULL,
                officer_agms TEXT NOT NULL DEFAULT '',
                officer_rank_short TEXT NOT NULL DEFAULT '',
                officer_rank_full TEXT NOT NULL DEFAULT '',
                ended_at TEXT,
                status TEXT NOT NULL CHECK(status IN ('OPEN','CLOSED'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_shift
                ON shifts(status) WHERE status='OPEN';

            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surname TEXT NOT NULL,
                given_name TEXT NOT NULL,
                birth_date TEXT,
                surname_norm TEXT NOT NULL,
                given_name_norm TEXT NOT NULL,
                surname_phonetic TEXT NOT NULL,
                given_name_phonetic TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_people_exact
                ON people(surname_norm, given_name_norm, birth_date);
            CREATE INDEX IF NOT EXISTS idx_people_phonetic
                ON people(surname_phonetic, given_name_phonetic);

            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                shift_id INTEGER,
                action_type TEXT NOT NULL,
                reason TEXT,
                occurred_at TEXT NOT NULL,
                protocol_no TEXT,
                passport_no TEXT,
                details_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_actions_person_time
                ON actions(person_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_actions_shift_time
                ON actions(shift_id, occurred_at ASC);

            CREATE TABLE IF NOT EXISTS fines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                shift_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                operation_type TEXT NOT NULL CHECK(operation_type IN ('IMPOSITION','PAYMENT')),
                fine_date TEXT NOT NULL,
                imposition_protocol TEXT,
                paravolo TEXT,
                nationality TEXT,
                passport_no TEXT,
                measure TEXT,
                amount INTEGER NOT NULL,
                collection_method TEXT,
                collection_protocol TEXT,
                responsible TEXT,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(shift_id) REFERENCES shifts(id),
                FOREIGN KEY(action_id) REFERENCES actions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_fines_shift ON fines(shift_id, id);
            CREATE INDEX IF NOT EXISTS idx_fines_person ON fines(person_id, occurred_at DESC);

            CREATE TABLE IF NOT EXISTS refusals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                shift_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                aa TEXT NOT NULL,
                refusal_year TEXT NOT NULL,
                protocol_prefix TEXT NOT NULL,
                protocol_no TEXT NOT NULL,
                refusal_date TEXT NOT NULL,
                refusal_time TEXT NOT NULL,
                sex TEXT,
                birth_date_display TEXT,
                passport_no TEXT,
                issue_date TEXT,
                reason TEXT NOT NULL,
                measure_country TEXT,
                measure_no TEXT,
                measure_from TEXT,
                measure_to TEXT,
                sis_country TEXT,
                sis_no TEXT,
                sis_from TEXT,
                sis_to TEXT,
                language TEXT NOT NULL,
                archive_path TEXT,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(shift_id) REFERENCES shifts(id),
                FOREIGN KEY(action_id) REFERENCES actions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_refusals_shift ON refusals(shift_id,id);
            CREATE INDEX IF NOT EXISTS idx_refusals_person ON refusals(person_id,occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_refusals_protocol ON refusals(protocol_prefix,protocol_no);

            CREATE TABLE IF NOT EXISTS receipt_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collector_name TEXT NOT NULL,
                collector_norm TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                archive_date TEXT,
                archive_seq INTEGER,
                archive_path TEXT,
                receiver_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL CHECK(status IN ('OPEN','CLOSED'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_receipt_list_per_collector
                ON receipt_lists(collector_norm) WHERE status='OPEN';

            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_list_id INTEGER NOT NULL,
                person_id INTEGER,
                occurred_at TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_type TEXT,
                passport_no TEXT,
                protocol_no TEXT,
                measure TEXT,
                paravolo TEXT,
                notes TEXT,
                action_id INTEGER,
                FOREIGN KEY(receipt_list_id) REFERENCES receipt_lists(id),
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(action_id) REFERENCES actions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_receipts_list ON receipts(receipt_list_id);
            CREATE INDEX IF NOT EXISTS idx_receipts_person ON receipts(person_id);

            CREATE TABLE IF NOT EXISTS daily_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL UNIQUE,
                updated_at TEXT NOT NULL,
                manual_json TEXT NOT NULL DEFAULT '{}',
                archive_path TEXT,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_daily_activity_shift ON daily_activity(shift_id);

            CREATE TABLE IF NOT EXISTS pending_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                resolved_at TEXT,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_pending_job_per_type
                ON pending_jobs(shift_id,job_type) WHERE resolved_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_pending_jobs_open
                ON pending_jobs(resolved_at,created_at);

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            # Migrate v0.1 databases in-place without destroying test data.
            shift_cols = self._columns(con, "shifts")
            for name in ("officer_agms", "officer_rank_short", "officer_rank_full"):
                if name not in shift_cols:
                    con.execute(f"ALTER TABLE shifts ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            receipt_list_cols = self._columns(con, "receipt_lists")
            if "receiver_name" not in receipt_list_cols:
                con.execute("ALTER TABLE receipt_lists ADD COLUMN receiver_name TEXT NOT NULL DEFAULT ''")
            receipt_cols = self._columns(con, "receipts")
            if "measure" not in receipt_cols:
                con.execute("ALTER TABLE receipts ADD COLUMN measure TEXT")
            if "paravolo" not in receipt_cols:
                con.execute("ALTER TABLE receipts ADD COLUMN paravolo TEXT")
            refusal_cols = self._columns(con, "refusals")
            for name in ("birth_place", "nationality", "residence", "passport_issuer", "origin_country"):
                if name not in refusal_cols:
                    con.execute(f"ALTER TABLE refusals ADD COLUMN {name} TEXT")
            con.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    def get_open_shift(self) -> sqlite3.Row | None:
        with self.connect() as con:
            return con.execute("SELECT * FROM shifts WHERE status='OPEN' ORDER BY id DESC LIMIT 1").fetchone()

    def get_shift(self, shift_id: int) -> sqlite3.Row | None:
        with self.connect() as con:
            return con.execute("SELECT * FROM shifts WHERE id=?", (shift_id,)).fetchone()

    def get_current_or_last_shift(self) -> sqlite3.Row | None:
        """Shift used by report buttons: open shift, otherwise latest closed shift."""
        with self.connect() as con:
            row = con.execute("SELECT * FROM shifts WHERE status='OPEN' ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                return row
            return con.execute("SELECT * FROM shifts WHERE status='CLOSED' ORDER BY id DESC LIMIT 1").fetchone()

    def start_shift(self, officer_name: str, started_at: datetime | None = None,
                    officer_agms: str = "", officer_rank_short: str = "",
                    officer_rank_full: str = "") -> int:
        officer_name = officer_name.strip()
        if not officer_name:
            raise ValueError("Απαιτείται Αξιωματικός Υπηρεσίας.")
        stamp = (started_at or datetime.now()).isoformat(timespec="seconds")
        with self.write() as con:
            existing = con.execute("SELECT id FROM shifts WHERE status='OPEN'").fetchone()
            if existing:
                raise ValueError("Υπάρχει ήδη ενεργή βάρδια.")
            cur = con.execute(
                "INSERT INTO shifts(started_at,officer_name,officer_agms,officer_rank_short,officer_rank_full,status) "
                "VALUES(?,?,?,?,?,'OPEN')",
                (stamp, officer_name, officer_agms.strip(), officer_rank_short.strip(), officer_rank_full.strip()),
            )
            return int(cur.lastrowid)

    def close_shift(self, ended_at: datetime | None = None) -> int:
        stamp = (ended_at or datetime.now()).isoformat(timespec="seconds")
        with self.write() as con:
            row = con.execute("SELECT id FROM shifts WHERE status='OPEN' ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                raise ValueError("Δεν υπάρχει ενεργή βάρδια.")
            con.execute("UPDATE shifts SET ended_at=?, status='CLOSED' WHERE id=?", (stamp, row["id"]))
            return int(row["id"])

    def get_or_create_person(self, surname: str, given_name: str, birth_date: str | None) -> int:
        sn, gn = normalize_text(surname), normalize_text(given_name)
        if not sn or not gn:
            raise ValueError("Επώνυμο και όνομα είναι υποχρεωτικά.")
        bd = normalize_birth_date(birth_date)
        with self.write() as con:
            row = con.execute(
                "SELECT id FROM people WHERE surname_norm=? AND given_name_norm=? "
                "AND COALESCE(birth_date,'')=COALESCE(?, '') ORDER BY id LIMIT 1",
                (sn, gn, bd),
            ).fetchone()
            if row:
                return int(row["id"])
            cur = con.execute(
                "INSERT INTO people(surname,given_name,birth_date,surname_norm,given_name_norm,"
                "surname_phonetic,given_name_phonetic,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (surname.strip(), given_name.strip(), bd, sn, gn, phonetic_key(surname), phonetic_key(given_name), datetime.now().isoformat(timespec="seconds")),
            )
            return int(cur.lastrowid)

    def add_action(self, person_id: int | None, action_type: str, reason: str = "", protocol_no: str = "",
                   passport_no: str = "", details: dict[str, Any] | None = None,
                   occurred_at: datetime | None = None) -> int:
        shift = self.get_open_shift()
        stamp = (occurred_at or datetime.now()).isoformat(timespec="seconds")
        with self.write() as con:
            cur = con.execute(
                "INSERT INTO actions(person_id,shift_id,action_type,reason,occurred_at,protocol_no,passport_no,details_json) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (person_id, shift["id"] if shift else None, action_type, reason.strip(), stamp,
                 protocol_no.strip(), passport_no.strip(), json.dumps(details or {}, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def search_people_exact(self, surname: str, given_name: str = "", birth_date: str = "", limit: int = 100):
        sn, gn, bd = normalize_text(surname), normalize_text(given_name), normalize_birth_date(birth_date)
        clauses, args = [], []
        if sn:
            clauses.append("surname_norm=?"); args.append(sn)
        if gn:
            clauses.append("given_name_norm=?"); args.append(gn)
        if bd:
            clauses.append("birth_date=?"); args.append(bd)
        if not clauses:
            return []
        sql = "SELECT * FROM people WHERE " + " AND ".join(clauses) + " ORDER BY surname_norm,given_name_norm LIMIT ?"
        args.append(limit)
        with self.connect() as con:
            return con.execute(sql, args).fetchall()

    def search_people_phonetic(self, surname: str, given_name: str = "", limit: int = 100):
        sn, gn = normalize_text(surname), normalize_text(given_name)
        sp, gp = phonetic_key(surname), phonetic_key(given_name)
        if not sn and not gn:
            return []
        clauses, args = [], []
        if sn:
            clauses.append("substr(surname_norm,1,1)=?"); args.append(sn[:1])
        if gn:
            clauses.append("substr(given_name_norm,1,1)=?"); args.append(gn[:1])
        sql = "SELECT * FROM people"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY surname_norm,given_name_norm LIMIT 1000"
        with self.connect() as con:
            candidates = con.execute(sql, args).fetchall()
        ranked = []
        for row in candidates:
            surname_score = 1.0
            given_score = 1.0
            if sn:
                surname_score = max(
                    SequenceMatcher(None, sn, row["surname_norm"]).ratio(),
                    SequenceMatcher(None, sp, row["surname_phonetic"]).ratio(),
                )
            if gn:
                given_score = max(
                    SequenceMatcher(None, gn, row["given_name_norm"]).ratio(),
                    SequenceMatcher(None, gp, row["given_name_phonetic"]).ratio(),
                )
            score = surname_score if not gn else (0.68 * surname_score + 0.32 * given_score)
            if score >= 0.68:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["surname_norm"], item[1]["given_name_norm"]))
        return [row for _, row in ranked[:limit]]

    def person_history(self, person_id: int):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM actions WHERE person_id=? ORDER BY occurred_at DESC, id DESC", (person_id,)
            ).fetchall()

    def person_profile(self, person_id: int) -> dict[str, object]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
            if not row:
                return {}
            latest = con.execute(
                "SELECT passport_no FROM actions WHERE person_id=? AND COALESCE(passport_no,'')<>'' "
                "ORDER BY occurred_at DESC,id DESC LIMIT 1", (person_id,)
            ).fetchone()
            cnt = con.execute("SELECT COUNT(*) AS n FROM actions WHERE person_id=?", (person_id,)).fetchone()
            return {
                "id": int(row["id"]),
                "surname": row["surname"],
                "given_name": row["given_name"],
                "birth_date": row["birth_date"] or "",
                "passport_no": latest["passport_no"] if latest else "",
                "actions_count": int(cnt["n"] if cnt else 0),
            }

    def autocomplete_values(self, field: str, limit: int = 500) -> list[str]:
        """Return recent distinct values for Excel-like field suggestions."""
        sources = {
            "surname": [("people", "surname")],
            "given_name": [("people", "given_name")],
            "passport": [("actions", "passport_no"), ("refusals", "passport_no"), ("fines", "passport_no")],
            "nationality": [("refusals", "nationality"), ("fines", "nationality")],
            "birth_place": [("refusals", "birth_place")],
            "residence": [("refusals", "residence")],
            "passport_issuer": [("refusals", "passport_issuer")],
            "origin_country": [("refusals", "origin_country")],
            "measure": [("fines", "measure")],
            "responsible": [("fines", "responsible")],
            "paravolo": [("fines", "paravolo")],
            "measure_country": [("refusals", "measure_country")],
            "measure_no": [("refusals", "measure_no")],
            "sis_country": [("refusals", "sis_country")],
            "sis_no": [("refusals", "sis_no")],
        }
        selected = sources.get(field, [])
        if not selected:
            return []
        values: list[str] = []
        seen: set[str] = set()
        with self.connect() as con:
            for table, column in selected:
                rows = con.execute(
                    f"SELECT {column} AS value FROM {table} "
                    f"WHERE TRIM(COALESCE({column},''))<>'' ORDER BY id DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
                for row in rows:
                    value = str(row["value"] or "").strip()
                    key = value.casefold()
                    if value and key not in seen:
                        seen.add(key)
                        values.append(value)
                        if len(values) >= int(limit):
                            return values
        return values

    def get_preference(self, key: str, default: str = "") -> str:
        with self.connect() as con:
            row = con.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_preference(self, key: str, value: str) -> None:
        with self.write() as con:
            con.execute(
                "INSERT INTO preferences(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)
            )

    def add_pending_job(self, shift_id: int, job_type: str, error: str) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.write() as con:
            row = con.execute(
                "SELECT id FROM pending_jobs WHERE shift_id=? AND job_type=? AND resolved_at IS NULL",
                (shift_id, job_type),
            ).fetchone()
            if row:
                con.execute(
                    "UPDATE pending_jobs SET updated_at=?, attempts=attempts+1, last_error=? WHERE id=?",
                    (now, str(error), row["id"]),
                )
                return int(row["id"])
            cur = con.execute(
                "INSERT INTO pending_jobs(shift_id,job_type,created_at,updated_at,attempts,last_error) "
                "VALUES(?,?,?,?,1,?)",
                (shift_id, job_type, now, now, str(error)),
            )
            return int(cur.lastrowid)

    def list_pending_jobs(self):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM pending_jobs WHERE resolved_at IS NULL ORDER BY created_at,id"
            ).fetchall()

    def pending_count(self) -> int:
        with self.connect() as con:
            row = con.execute("SELECT COUNT(*) AS n FROM pending_jobs WHERE resolved_at IS NULL").fetchone()
            return int(row["n"] if row else 0)

    def resolve_pending_job(self, job_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.write() as con:
            con.execute(
                "UPDATE pending_jobs SET resolved_at=?, updated_at=?, last_error='' WHERE id=?",
                (now, now, job_id),
            )

    def fail_pending_job(self, job_id: int, error: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.write() as con:
            con.execute(
                "UPDATE pending_jobs SET updated_at=?, attempts=attempts+1, last_error=? WHERE id=?",
                (now, str(error), job_id),
            )
