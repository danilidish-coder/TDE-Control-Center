from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from app.core.db import Database
from app.core.paths import archive_root, preview_root, resource_path, resolve_runtime_path
from app.core.textnorm import normalize_birth_date, normalize_text, phonetic_key
from app.services.pdf_preview import open_document_preview
from app.services.protocol_workbook import ProtocolWorkbookWriter


def safe_folder_name(value: str) -> str:
    value = value.strip().upper()
    value = re.sub(r'[<>:"/\\|?*]+', '_', value)
    return value.strip(' .') or 'ΧΩΡΙΣ_ΟΝΟΜΑ'


class ReceiptService:
    def __init__(self, db: Database, writer=None):
        self.db = db
        self.writer = writer or ProtocolWorkbookWriter(resource_path("Fine_Protocol_Base.xlsx"))

    def get_open_list(self, collector_name: str):
        norm = normalize_text(collector_name)
        with self.db.connect() as con:
            return con.execute(
                "SELECT * FROM receipt_lists WHERE collector_norm=? AND status='OPEN' ORDER BY id DESC LIMIT 1", (norm,)
            ).fetchone()

    def get_list(self, list_id: int):
        with self.db.connect() as con:
            return con.execute("SELECT * FROM receipt_lists WHERE id=?", (int(list_id),)).fetchone()

    def _receipts_for_list(self, list_id: int):
        with self.db.connect() as con:
            return con.execute(
                "SELECT r.*,p.surname,p.given_name,p.birth_date FROM receipts r "
                "LEFT JOIN people p ON p.id=r.person_id WHERE r.receipt_list_id=? ORDER BY r.id",
                (int(list_id),),
            ).fetchall()

    def ensure_open_list(self, collector_name: str) -> int:
        collector_name = collector_name.strip()
        if not collector_name:
            raise ValueError("Απαιτείται όνομα αστυνομικού/εισπράττοντα.")
        existing = self.get_open_list(collector_name)
        if existing:
            return int(existing["id"])
        with self.db.write() as con:
            row = con.execute(
                "SELECT id FROM receipt_lists WHERE collector_norm=? AND status='OPEN' ORDER BY id DESC LIMIT 1",
                (normalize_text(collector_name),),
            ).fetchone()
            if row:
                return int(row["id"])
            cur = con.execute(
                "INSERT INTO receipt_lists(collector_name,collector_norm,opened_at,status) VALUES(?,?,?,'OPEN')",
                (collector_name, normalize_text(collector_name), datetime.now().isoformat(timespec="seconds")),
            )
            return int(cur.lastrowid)

    def add_receipt(self, collector_name: str, surname: str, given_name: str, birth_date: str,
                    amount: float, payment_type: str = "", passport_no: str = "", protocol_no: str = "",
                    measure: str = "", paravolo: str = "", notes: str = "") -> int:
        collector_name = collector_name.strip()
        surname = surname.strip(); given_name = given_name.strip()
        if not collector_name:
            raise ValueError("Απαιτείται όνομα αστυνομικού/εισπράττοντα.")
        if not surname or not given_name:
            raise ValueError("Επώνυμο και όνομα είναι υποχρεωτικά.")
        if float(amount) <= 0:
            raise ValueError("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
        collector_norm = normalize_text(collector_name)
        sn, gn = normalize_text(surname), normalize_text(given_name)
        bd = normalize_birth_date(birth_date)
        now = datetime.now().isoformat(timespec="seconds")
        with self.db.write() as con:
            row = con.execute(
                "SELECT id FROM receipt_lists WHERE collector_norm=? AND status='OPEN' ORDER BY id DESC LIMIT 1",
                (collector_norm,),
            ).fetchone()
            if row:
                list_id = int(row["id"])
            else:
                cur = con.execute(
                    "INSERT INTO receipt_lists(collector_name,collector_norm,opened_at,status) VALUES(?,?,?,'OPEN')",
                    (collector_name, collector_norm, now),
                )
                list_id = int(cur.lastrowid)
            person = con.execute(
                "SELECT id FROM people WHERE surname_norm=? AND given_name_norm=? "
                "AND COALESCE(birth_date,'')=COALESCE(?, '') ORDER BY id LIMIT 1",
                (sn, gn, bd),
            ).fetchone()
            if person:
                person_id = int(person["id"])
            else:
                cur = con.execute(
                    "INSERT INTO people(surname,given_name,birth_date,surname_norm,given_name_norm,"
                    "surname_phonetic,given_name_phonetic,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (surname, given_name, bd, sn, gn, phonetic_key(surname), phonetic_key(given_name), now),
                )
                person_id = int(cur.lastrowid)
            shift = con.execute("SELECT id FROM shifts WHERE status='OPEN' ORDER BY id DESC LIMIT 1").fetchone()
            action = con.execute(
                "INSERT INTO actions(person_id,shift_id,action_type,reason,occurred_at,protocol_no,passport_no,details_json) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (person_id, shift["id"] if shift else None, "PAYMENT", payment_type.strip(), now,
                 protocol_no.strip(), passport_no.strip(),
                 __import__("json").dumps({"amount": float(amount), "collector": collector_name, "receipt_list_id": list_id}, ensure_ascii=False)),
            )
            action_id = int(action.lastrowid)
            cur = con.execute(
                "INSERT INTO receipts(receipt_list_id,person_id,occurred_at,amount,payment_type,passport_no,protocol_no,measure,paravolo,notes,action_id) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (list_id, person_id, now, float(amount), payment_type.strip(), passport_no.strip(), protocol_no.strip(),
                 measure.strip(), paravolo.strip(), notes.strip(), action_id),
            )
            return int(cur.lastrowid)

    def preview_list(self, list_id: int) -> Path:
        row = self.get_list(list_id)
        if not row:
            raise ValueError("Δεν βρέθηκε η επιλεγμένη Λίστα Εισπράξεων.")
        receipts = self._receipts_for_list(list_id)
        if not receipts:
            raise ValueError("Η λίστα δεν περιέχει εισπράξεις.")

        if row["status"] == "CLOSED" and row["archive_path"]:
            workbook = resolve_runtime_path(row["archive_path"])
            if not workbook.exists():
                workbook = self.refresh_archived_list(list_id)
        else:
            workbook = preview_root() / f"ΠΡΟΕΠΙΣΚΟΠΗΣΗ_ΛΙΣΤΑΣ_ΕΙΣΠΡΑΞΕΩΝ_{int(list_id)}.xlsx"
            pdf_path = workbook.with_suffix(".pdf")
            self.writer.write(
                workbook,
                [dict(x) for x in receipts],
                collector_name=row["collector_name"] or "",
                receiver_name="",
                handover_at=datetime.now(),
                pdf_path=pdf_path,
            )
            return pdf_path if pdf_path.exists() else workbook

        pdf_path = workbook.with_suffix(".pdf")
        return pdf_path if pdf_path.exists() else workbook

    def close_list(self, collector_name: str, receiver_name: str | datetime = "", when: datetime | None = None) -> Path:
        row = self.get_open_list(collector_name)
        if not row:
            raise ValueError("Δεν υπάρχει ενεργή λίστα για κλείσιμο.")
        legacy_return = False
        if isinstance(receiver_name, datetime):
            when = receiver_name
            receiver_name = "ΜΗ ΚΑΤΑΧΩΡΙΣΜΕΝΟΣ"
            legacy_return = True
        else:
            receiver_name = receiver_name.strip()
            if not receiver_name:
                receiver_name = "ΜΗ ΚΑΤΑΧΩΡΙΣΜΕΝΟΣ"
                legacy_return = True
        when = when or datetime.now()
        day = when.strftime("%d-%m-%Y")
        collector_folder = archive_root() / "ΕΙΣΠΡΑΞΕΙΣ" / safe_folder_name(row["collector_name"])
        collector_folder.mkdir(parents=True, exist_ok=True)
        with self.db.connect() as con:
            seq_row = con.execute(
                "SELECT COALESCE(MAX(archive_seq),0)+1 AS seq FROM receipt_lists WHERE collector_norm=? AND archive_date=?",
                (row["collector_norm"], day),
            ).fetchone()
            seq = int(seq_row["seq"])
            receipts = con.execute(
                "SELECT r.*, p.surname, p.given_name, p.birth_date FROM receipts r "
                "LEFT JOIN people p ON p.id=r.person_id WHERE r.receipt_list_id=? ORDER BY r.id",
                (row["id"],),
            ).fetchall()
        if not receipts:
            raise ValueError("Η ενεργή λίστα δεν περιέχει εισπράξεις.")
        path = collector_folder / f"{day}_{seq:02d}.xlsx"
        pdf_path = path.with_suffix(".pdf")
        if legacy_return:
            self.writer.write(path, [dict(x) for x in receipts])
        else:
            self.writer.write(
                path,
                [dict(x) for x in receipts],
                collector_name=row["collector_name"] or "",
                receiver_name=receiver_name,
                handover_at=when,
                pdf_path=pdf_path,
            )
        with self.db.write() as con:
            current = con.execute("SELECT status FROM receipt_lists WHERE id=?", (row["id"],)).fetchone()
            if not current or current["status"] != "OPEN":
                raise RuntimeError("Η λίστα άλλαξε κατάσταση από άλλον σταθμό. Ελέγξτε το Αρχείο Εισπράξεων.")
            con.execute(
                "UPDATE receipt_lists SET closed_at=?,archive_date=?,archive_seq=?,archive_path=?,receiver_name=?,status='CLOSED' WHERE id=?",
                (when.isoformat(timespec="seconds"), day, seq, str(path), receiver_name, row["id"]),
            )
        return path if legacy_return else (pdf_path if pdf_path.exists() else path)

    def refresh_archived_list(self, list_id: int) -> Path | None:
        with self.db.lock.acquire():
            with self.db.connect() as con:
                row = con.execute("SELECT * FROM receipt_lists WHERE id=?", (list_id,)).fetchone()
                if not row:
                    raise ValueError("Δεν βρέθηκε η Λίστα Εισπράξεων.")
                if row["status"] != "CLOSED":
                    return None
                if not row["archive_path"]:
                    raise ValueError("Λείπει η διαδρομή της αρχειοθετημένης Λίστας Εισπράξεων.")
                receipts = con.execute(
                    "SELECT r.*,p.surname,p.given_name,p.birth_date FROM receipts r "
                    "LEFT JOIN people p ON p.id=r.person_id WHERE r.receipt_list_id=? ORDER BY r.id", (list_id,)
                ).fetchall()
            workbook = resolve_runtime_path(row["archive_path"])
            handover_at = datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else datetime.now()
            if (row["receiver_name"] or "") == "ΜΗ ΚΑΤΑΧΩΡΙΣΜΕΝΟΣ":
                self.writer.write(workbook, [dict(x) for x in receipts])
            else:
                self.writer.write(
                    workbook,
                    [dict(x) for x in receipts],
                    collector_name=row["collector_name"] or "",
                    receiver_name=row["receiver_name"] or "",
                    handover_at=handover_at,
                    pdf_path=workbook.with_suffix(".pdf"),
                )
            return workbook

    def search_receipts(self, query: str = "", collector: str = "", limit: int = 200):
        q = f"%{normalize_text(query)}%" if query.strip() else None
        c = normalize_text(collector) if collector.strip() else None
        sql = """
        SELECT r.id,r.occurred_at,r.amount,r.payment_type,r.passport_no,r.protocol_no,r.measure,r.paravolo,
               p.surname,p.given_name,p.birth_date,
               l.collector_name,l.status,l.archive_date,l.archive_seq,l.archive_path,l.receiver_name
        FROM receipts r
        JOIN receipt_lists l ON l.id=r.receipt_list_id
        LEFT JOIN people p ON p.id=r.person_id
        WHERE 1=1
        """
        args = []
        if q:
            sql += " AND (p.surname_norm LIKE ? OR p.given_name_norm LIKE ? OR COALESCE(r.passport_no,'') LIKE ? OR COALESCE(r.protocol_no,'') LIKE ?)"
            args += [q, q, f"%{query.strip()}%", f"%{query.strip()}%"]
        if c:
            sql += " AND l.collector_norm=?"; args.append(c)
        sql += " ORDER BY r.occurred_at DESC,r.id DESC LIMIT ?"; args.append(limit)
        with self.db.connect() as con:
            return con.execute(sql, args).fetchall()

    def list_lists(self, collector: str = "", limit: int = 200):
        c = normalize_text(collector) if collector.strip() else None
        sql = "SELECT * FROM receipt_lists WHERE 1=1"; args = []
        if c:
            sql += " AND collector_norm=?"; args.append(c)
        sql += " ORDER BY opened_at DESC,id DESC LIMIT ?"; args.append(limit)
        with self.db.connect() as con:
            return con.execute(sql, args).fetchall()

    def collector_names(self) -> list[str]:
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT collector_name, MAX(id) last_id FROM receipt_lists "
                "GROUP BY collector_norm ORDER BY collector_name"
            ).fetchall()
            return [r["collector_name"] for r in rows]

    def list_summaries(self, collector: str = "", limit: int = 200):
        c = normalize_text(collector) if collector.strip() else None
        sql = """
        SELECT l.*, COUNT(r.id) AS receipt_count, COALESCE(SUM(r.amount),0) AS total_amount
        FROM receipt_lists l
        LEFT JOIN receipts r ON r.receipt_list_id=l.id
        WHERE 1=1
        """
        args = []
        if c:
            sql += " AND l.collector_norm=?"; args.append(c)
        sql += " GROUP BY l.id ORDER BY CASE WHEN l.status='OPEN' THEN 0 ELSE 1 END, l.opened_at DESC,l.id DESC LIMIT ?"
        args.append(limit)
        with self.db.connect() as con:
            return con.execute(sql, args).fetchall()

    @staticmethod
    def open_file(path: str | Path) -> Path:
        return open_document_preview(resolve_runtime_path(path))
