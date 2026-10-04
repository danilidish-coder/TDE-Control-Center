from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .fines_engine import FineEntry
from .refusals_engine import RefusalEntry
from .fine_protocol import ProtocolReceipt


class StateStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'tde.sqlite3'
        with sqlite3.connect(self.db) as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS fines(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                op_date TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS refusals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                op_date TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity_keys(
                key TEXT PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pending_activity(
                key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target_cell TEXT NOT NULL,
                log_sheet TEXT NOT NULL,
                event_type TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'PENDING',
                last_attempt TEXT,
                last_error TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS fine_protocol_receipts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fine_id INTEGER NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                op_date TEXT NOT NULL,
                officer_key TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                protocol_no TEXT,
                amount INTEGER NOT NULL,
                collection_method TEXT,
                measure TEXT,
                paravolo TEXT,
                UNIQUE(op_date, officer_key, sequence)
            );
            CREATE TABLE IF NOT EXISTS fine_protocol_rows(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fine_id INTEGER NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                protocol_bucket TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                protocol_no TEXT,
                amount INTEGER NOT NULL,
                collection_method TEXT,
                measure TEXT,
                paravolo TEXT,
                UNIQUE(protocol_bucket, sequence)
            );
            ''')
            # Safe migration from the first prototype database.
            for table in ('fines', 'refusals'):
                cols = {r[1] for r in con.execute(f'PRAGMA table_info({table})')}
                if 'op_date' not in cols:
                    con.execute(f'ALTER TABLE {table} ADD COLUMN op_date TEXT')
            pending_cols = {r[1] for r in con.execute('PRAGMA table_info(pending_activity)')}
            if 'event_type' not in pending_cols:
                con.execute("ALTER TABLE pending_activity ADD COLUMN event_type TEXT NOT NULL DEFAULT ''")

    def add_fine(self, e: FineEntry, op_date: date | None = None) -> int:
        with sqlite3.connect(self.db) as c:
            cur=c.execute(
                'INSERT INTO fines(op_date,payload) VALUES(?,?)',
                ((op_date.isoformat() if op_date else None), json.dumps(asdict(e), ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def add_protocol_receipt(self, *, fine_id: int, protocol_bucket: str,
                             protocol_no: str, amount: int, collection_method: str,
                             measure: str, paravolo: str) -> ProtocolReceipt:
        """Allocate A/A exactly like the selected VBA protocol sheet."""
        bucket=str(protocol_bucket or '').strip() or 'ΠΡΩΤΟΚΟΛΛΟ'
        with sqlite3.connect(self.db) as c:
            existing=c.execute(
                "SELECT sequence,protocol_no,amount,collection_method,measure,paravolo,protocol_bucket FROM fine_protocol_rows WHERE fine_id=?",
                (int(fine_id),)
            ).fetchone()
            if existing:
                return ProtocolReceipt(
                    int(existing[0]), existing[1] or '', int(existing[2]),
                    existing[3] or '', existing[4] or '', existing[5] or '',
                    protocol_bucket=existing[6] or bucket,
                )
            seq=int(c.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM fine_protocol_rows WHERE protocol_bucket=?",
                (bucket,)
            ).fetchone()[0])
            c.execute(
                "INSERT INTO fine_protocol_rows (fine_id,protocol_bucket,sequence,protocol_no,amount,collection_method,measure,paravolo) VALUES(?,?,?,?,?,?,?,?)",
                (int(fine_id),bucket,seq,protocol_no,int(amount),collection_method,measure,paravolo)
            )
        return ProtocolReceipt(
            seq, protocol_no, int(amount), collection_method, measure, paravolo,
            protocol_bucket=bucket,
        )

    def record_protocol_receipt(self, *, fine_id: int, receipt: ProtocolReceipt) -> ProtocolReceipt:
        """Store the A/A returned by the actual workbook; workbook is authoritative."""
        bucket=str(receipt.protocol_bucket or '').strip() or 'ΠΡΩΤΟΚΟΛΛΟ'
        with sqlite3.connect(self.db) as c:
            existing=c.execute(
                "SELECT sequence,protocol_no,amount,collection_method,measure,paravolo,protocol_bucket FROM fine_protocol_rows WHERE fine_id=?",
                (int(fine_id),)
            ).fetchone()
            if existing:
                return ProtocolReceipt(int(existing[0]), existing[1] or '', int(existing[2]), existing[3] or '', existing[4] or '', existing[5] or '', protocol_bucket=existing[6] or bucket)
            c.execute(
                "INSERT INTO fine_protocol_rows (fine_id,protocol_bucket,sequence,protocol_no,amount,collection_method,measure,paravolo) VALUES(?,?,?,?,?,?,?,?)",
                (int(fine_id),bucket,int(receipt.sequence),receipt.protocol_no,int(receipt.amount),receipt.collection_method,receipt.measure,receipt.paravolo)
            )
        return receipt

    def protocol_receipts(self, protocol_bucket: str) -> list[ProtocolReceipt]:
        bucket=str(protocol_bucket or '').strip() or 'ΠΡΩΤΟΚΟΛΛΟ'
        with sqlite3.connect(self.db) as c:
            rows=c.execute(
                "SELECT sequence,protocol_no,amount,collection_method,measure,paravolo FROM fine_protocol_rows WHERE protocol_bucket=? ORDER BY sequence",
                (bucket,)
            ).fetchall()
        return [
            ProtocolReceipt(
                int(r[0]), r[1] or '', int(r[2]), r[3] or '', r[4] or '', r[5] or '',
                protocol_bucket=bucket,
            )
            for r in rows
        ]

    def add_refusal(self, e: RefusalEntry, op_date: date | None = None) -> int:
        with sqlite3.connect(self.db) as c:
            cur = c.execute(
                'INSERT INTO refusals(op_date,payload) VALUES(?,?)',
                ((op_date.isoformat() if op_date else None), json.dumps(asdict(e), ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def refusals_for_date(self, op_date: date) -> list[RefusalEntry]:
        with sqlite3.connect(self.db) as c:
            rows = c.execute(
                'SELECT payload FROM refusals WHERE op_date=? ORDER BY id',
                (op_date.isoformat(),),
            ).fetchall()
        return [RefusalEntry(**json.loads(x[0])) for x in rows]

    def last_refusal_id(self) -> int:
        with sqlite3.connect(self.db) as c:
            return int(c.execute('SELECT COALESCE(MAX(id),0) FROM refusals').fetchone()[0])

    def refusals_after_id(self, refusal_id: int) -> list[RefusalEntry]:
        with sqlite3.connect(self.db) as c:
            rows = c.execute(
                'SELECT payload FROM refusals WHERE id>? ORDER BY id',
                (max(0, int(refusal_id)),),
            ).fetchall()
        return [RefusalEntry(**json.loads(x[0])) for x in rows]

    def fines_for_date(self, op_date: date) -> list[FineEntry]:
        with sqlite3.connect(self.db) as c:
            rows = c.execute(
                'SELECT payload FROM fines WHERE op_date=? ORDER BY id',
                (op_date.isoformat(),),
            ).fetchall()
        return [FineEntry(**json.loads(x[0])) for x in rows]

    def once(self, key: str) -> bool:
        try:
            with sqlite3.connect(self.db) as c:
                c.execute('INSERT INTO activity_keys(key) VALUES(?)', (key,))
            return True
        except sqlite3.IntegrityError:
            return False

    # -------------------- ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ / SAFE QUEUE --------------------
    def queue_activity(self, *, key: str, source: str, target_cell: str, log_sheet: str, event_type: str = '', error: str = '') -> None:
        """Queue once; repeated failures only refresh the reason/attempt timestamp."""
        with sqlite3.connect(self.db) as c:
            c.execute(
                '''
                INSERT INTO pending_activity(key,source,target_cell,log_sheet,event_type,status,last_attempt,last_error)
                VALUES(?,?,?,?,?, 'PENDING', CURRENT_TIMESTAMP, ?)
                ON CONFLICT(key) DO UPDATE SET
                    source=excluded.source,
                    target_cell=excluded.target_cell,
                    log_sheet=excluded.log_sheet,
                    event_type=excluded.event_type,
                    status=CASE WHEN pending_activity.status='DONE' THEN 'DONE' ELSE 'PENDING' END,
                    last_attempt=CURRENT_TIMESTAMP,
                    last_error=CASE WHEN pending_activity.status='DONE' THEN pending_activity.last_error ELSE excluded.last_error END
                ''',
                (key, source, target_cell, log_sheet, event_type, error),
            )

    def pending_activities(self, limit: int = 100) -> list[dict[str, str]]:
        with sqlite3.connect(self.db) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                '''SELECT key,source,target_cell,log_sheet,event_type,created_at,status,last_attempt,last_error
                   FROM pending_activity WHERE status='PENDING' ORDER BY created_at,key LIMIT ?''',
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_activity_done(self, key: str) -> None:
        with sqlite3.connect(self.db) as c:
            c.execute(
                "UPDATE pending_activity SET status='DONE', last_attempt=CURRENT_TIMESTAMP, last_error='' WHERE key=?",
                (key,),
            )

    def mark_activity_error(self, key: str, error: str) -> None:
        with sqlite3.connect(self.db) as c:
            c.execute(
                "UPDATE pending_activity SET status='PENDING', last_attempt=CURRENT_TIMESTAMP, last_error=? WHERE key=?",
                (error, key),
            )

    def pending_activity_count(self) -> int:
        with sqlite3.connect(self.db) as c:
            return int(c.execute("SELECT COUNT(*) FROM pending_activity WHERE status='PENDING'").fetchone()[0])
