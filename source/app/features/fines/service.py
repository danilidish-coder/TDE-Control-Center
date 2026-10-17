from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.core.db import Database
from app.core.paths import archive_root, preview_root, resource_path
from app.core.textnorm import normalize_birth_date, normalize_text, phonetic_key
from app.shared.documents.common import fmt_date
from app.features.fines.documents import ALLOWED_AMOUNTS, FineEntry, FineReportEngine
from app.features.daily_activity.service import DailyActivityService
from app.features.reports.pending import DAILY_ACTIVITY, FINES_REPORT, PendingResult, PendingService
from app.features.receipts.service import ReceiptService


class FineService:
    def __init__(self, db: Database):
        self.db = db
        self.engine = FineReportEngine(resource_path("Anafora_base.docx"))

    @staticmethod
    def _validate(kind: str, entry: FineEntry) -> None:
        kind = kind.upper().strip()
        if kind not in {"IMPOSITION", "PAYMENT"}:
            raise ValueError("Μη έγκυρος τύπος πράξης προστίμου.")
        if not entry.surname.strip():
            raise ValueError("Απαιτείται Επώνυμο.")
        if int(entry.amount) not in ALLOWED_AMOUNTS:
            raise ValueError("Χρηματικό ποσό: επιτρέπεται μόνο 600 ή 1200.")
        fmt_date(entry.date, "/")
        if entry.birth_date.strip():
            fmt_date(entry.birth_date, "/")
        if kind == "PAYMENT" and not entry.responsible.strip():
            raise ValueError("Στην είσπραξη απαιτείται ο αστυνομικός/εισπράττων.")

    def add_fine(self, kind: str, entry: FineEntry, occurred_at: datetime | None = None) -> int:
        kind = kind.upper().strip()
        self._validate(kind, entry)
        shift = self.db.get_open_shift()
        if not shift:
            raise ValueError("Δεν υπάρχει ενεργή βάρδια. Πρώτα ΕΝΑΡΞΗ ΒΑΡΔΙΑΣ.")
        now_dt = occurred_at or datetime.now()
        now = now_dt.isoformat(timespec="seconds")
        sn, gn = normalize_text(entry.surname), normalize_text(entry.name)
        # Preserve the old VBA requirement: only surname is mandatory. Blank given name is allowed.
        bd = normalize_birth_date(entry.birth_date)
        action_type = "FINE_IMPOSITION" if kind == "IMPOSITION" else "PAYMENT"
        action_reason = entry.measure.strip() if kind == "IMPOSITION" else (entry.collection_method.strip() or "ΕΙΣΠΡΑΞΗ")
        protocol = entry.imposition_protocol.strip() if kind == "IMPOSITION" else entry.collection_protocol.strip()
        with self.db.write() as con:
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
                    (entry.surname.strip(), entry.name.strip(), bd, sn, gn, phonetic_key(entry.surname), phonetic_key(entry.name), now),
                )
                person_id = int(cur.lastrowid)

            details = {
                "amount": int(entry.amount),
                "nationality": entry.nationality.strip(),
                "measure": entry.measure.strip(),
                "paravolo": entry.paravolo.strip(),
                "collection_method": entry.collection_method.strip(),
                "responsible": entry.responsible.strip(),
                "operation_type": kind,
            }
            action = con.execute(
                "INSERT INTO actions(person_id,shift_id,action_type,reason,occurred_at,protocol_no,passport_no,details_json) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (person_id, int(shift["id"]), action_type, action_reason, now, protocol,
                 entry.passport.strip(), json.dumps(details, ensure_ascii=False)),
            )
            action_id = int(action.lastrowid)
            fine = con.execute(
                "INSERT INTO fines(person_id,shift_id,action_id,occurred_at,operation_type,fine_date,imposition_protocol,paravolo,"
                "nationality,passport_no,measure,amount,collection_method,collection_protocol,responsible) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (person_id, int(shift["id"]), action_id, now, kind, fmt_date(entry.date, "/"),
                 entry.imposition_protocol.strip(), entry.paravolo.strip(), entry.nationality.strip(), entry.passport.strip(),
                 entry.measure.strip(), int(entry.amount), entry.collection_method.strip(), entry.collection_protocol.strip(), entry.responsible.strip()),
            )
            fine_id = int(fine.lastrowid)

            if kind == "PAYMENT":
                collector = entry.responsible.strip()
                collector_norm = normalize_text(collector)
                lst = con.execute(
                    "SELECT id FROM receipt_lists WHERE collector_norm=? AND status='OPEN' ORDER BY id DESC LIMIT 1",
                    (collector_norm,),
                ).fetchone()
                if lst:
                    list_id = int(lst["id"])
                else:
                    cur = con.execute(
                        "INSERT INTO receipt_lists(collector_name,collector_norm,opened_at,status) VALUES(?,?,?,'OPEN')",
                        (collector, collector_norm, now),
                    )
                    list_id = int(cur.lastrowid)
                con.execute(
                    "INSERT INTO receipts(receipt_list_id,person_id,occurred_at,amount,payment_type,passport_no,protocol_no,measure,paravolo,notes,action_id) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (list_id, person_id, now, float(entry.amount), entry.collection_method.strip(), entry.passport.strip(),
                     entry.collection_protocol.strip(), entry.measure.strip(), entry.paravolo.strip(), "", action_id),
                )
            return fine_id

    def fines_for_shift(self, shift_id: int):
        with self.db.connect() as con:
            return con.execute(
                "SELECT f.*,p.surname,p.given_name,p.birth_date FROM fines f JOIN people p ON p.id=f.person_id "
                "WHERE f.shift_id=? ORDER BY f.id", (shift_id,)
            ).fetchall()

    def get_fine(self, fine_id: int):
        with self.db.connect() as con:
            return con.execute(
                "SELECT f.*,p.surname,p.given_name,p.birth_date FROM fines f "
                "JOIN people p ON p.id=f.person_id WHERE f.id=?", (fine_id,)
            ).fetchone()

    @staticmethod
    def _corrected_person(con, row, entry: FineEntry) -> int:
        """Correct this act's identity without rewriting another person's history."""
        old_id = int(row["person_id"])
        bd = normalize_birth_date(entry.birth_date)
        if (row["surname"], row["given_name"], row["birth_date"] or "") == (
            entry.surname.strip(), entry.name.strip(), bd or ""
        ):
            return old_id
        sn, gn = normalize_text(entry.surname), normalize_text(entry.name)
        match = con.execute(
            "SELECT id FROM people WHERE id<>? AND surname_norm=? AND given_name_norm=? "
            "AND COALESCE(birth_date,'')=COALESCE(?,'') ORDER BY id LIMIT 1",
            (old_id, sn, gn, bd),
        ).fetchone()
        if match:
            return int(match["id"])
        shared = con.execute(
            "SELECT EXISTS(SELECT 1 FROM actions WHERE person_id=? AND id<>?) "
            "OR EXISTS(SELECT 1 FROM fines WHERE person_id=? AND id<>?) "
            "OR EXISTS(SELECT 1 FROM refusals WHERE person_id=?) "
            "OR EXISTS(SELECT 1 FROM receipts WHERE person_id=? AND (action_id IS NULL OR action_id<>?))",
            (old_id, row["action_id"], old_id, row["id"], old_id, old_id, row["action_id"]),
        ).fetchone()[0]
        values = (entry.surname.strip(), entry.name.strip(), bd, sn, gn,
                  phonetic_key(entry.surname), phonetic_key(entry.name))
        if not shared:
            con.execute(
                "UPDATE people SET surname=?,given_name=?,birth_date=?,surname_norm=?,given_name_norm=?,"
                "surname_phonetic=?,given_name_phonetic=? WHERE id=?", (*values, old_id),
            )
            return old_id
        cur = con.execute(
            "INSERT INTO people(surname,given_name,birth_date,surname_norm,given_name_norm,"
            "surname_phonetic,given_name_phonetic,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (*values, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)

    def update_fine(self, fine_id: int, entry: FineEntry, *, expected_entry: FineEntry | None = None) -> PendingResult:
        affected_lists: set[int] = set()
        with self.db.write() as con:
            row = con.execute(
                "SELECT f.*,p.surname,p.given_name,p.birth_date FROM fines f "
                "JOIN people p ON p.id=f.person_id WHERE f.id=?", (fine_id,)
            ).fetchone()
            if not row:
                raise ValueError("Δεν βρέθηκε η επιλεγμένη πράξη.")
            kind = row["operation_type"]
            self._validate(kind, entry)
            if kind == "IMPOSITION":
                entry = replace(entry, paravolo="", collection_method="", collection_protocol="")
            if expected_entry is not None and self._row_to_entry(row, for_report=False) != expected_entry:
                raise ValueError("Η πράξη άλλαξε από άλλον σταθμό. Πατήστε ΑΝΑΝΕΩΣΗ και επιλέξτε την ξανά.")
            action = con.execute("SELECT * FROM actions WHERE id=?", (row["action_id"],)).fetchone()
            if not action:
                raise ValueError("Δεν βρέθηκε η συνδεδεμένη πράξη στο ιστορικό.")
            receipts = con.execute(
                "SELECT r.*,l.collector_norm FROM receipts r JOIN receipt_lists l ON l.id=r.receipt_list_id "
                "WHERE r.action_id=?", (row["action_id"],)
            ).fetchall()
            if kind == "PAYMENT" and len(receipts) != 1:
                raise ValueError("Η είσπραξη δεν έχει μοναδική συνδεδεμένη εγγραφή στη Λίστα Εισπράξεων.")
            person_id = self._corrected_person(con, row, entry)
            details = json.loads(action["details_json"] or "{}")
            details.update(amount=int(entry.amount), nationality=entry.nationality.strip(), measure=entry.measure.strip(),
                           paravolo=entry.paravolo.strip(), collection_method=entry.collection_method.strip(),
                           responsible=entry.responsible.strip(), operation_type=kind)
            reason = entry.measure.strip() if kind == "IMPOSITION" else (entry.collection_method.strip() or "ΕΙΣΠΡΑΞΗ")
            protocol = entry.imposition_protocol.strip() if kind == "IMPOSITION" else entry.collection_protocol.strip()
            con.execute(
                "UPDATE actions SET person_id=?,reason=?,protocol_no=?,passport_no=?,details_json=? WHERE id=?",
                (person_id, reason, protocol, entry.passport.strip(), json.dumps(details, ensure_ascii=False), row["action_id"]),
            )
            con.execute(
                "UPDATE fines SET person_id=?,fine_date=?,imposition_protocol=?,paravolo=?,nationality=?,passport_no=?,"
                "measure=?,amount=?,collection_method=?,collection_protocol=?,responsible=? WHERE id=?",
                (person_id, fmt_date(entry.date, "/"), entry.imposition_protocol.strip(), entry.paravolo.strip(),
                 entry.nationality.strip(), entry.passport.strip(), entry.measure.strip(), int(entry.amount),
                 entry.collection_method.strip(), entry.collection_protocol.strip(), entry.responsible.strip(), fine_id),
            )
            if kind == "PAYMENT":
                receipt = receipts[0]
                list_id = int(receipt["receipt_list_id"])
                affected_lists.add(list_id)
                collector = entry.responsible.strip()
                collector_norm = normalize_text(collector)
                if collector_norm != receipt["collector_norm"]:
                    target = con.execute(
                        "SELECT id FROM receipt_lists WHERE collector_norm=? AND status='OPEN' ORDER BY id DESC LIMIT 1",
                        (collector_norm,),
                    ).fetchone()
                    if target:
                        list_id = int(target["id"])
                    else:
                        cur = con.execute(
                            "INSERT INTO receipt_lists(collector_name,collector_norm,opened_at,status) VALUES(?,?,?,'OPEN')",
                            (collector, collector_norm, datetime.now().isoformat(timespec="seconds")),
                        )
                        list_id = int(cur.lastrowid)
                    affected_lists.add(list_id)
                con.execute(
                    "UPDATE receipts SET receipt_list_id=?,person_id=?,amount=?,payment_type=?,passport_no=?,"
                    "protocol_no=?,measure=?,paravolo=? WHERE id=?",
                    (list_id, person_id, float(entry.amount), entry.collection_method.strip(), entry.passport.strip(),
                     entry.collection_protocol.strip(), entry.measure.strip(), entry.paravolo.strip(), receipt["id"]),
                )
            old_person = int(row["person_id"])
            if old_person != person_id:
                con.execute(
                    "DELETE FROM people WHERE id=? AND NOT EXISTS(SELECT 1 FROM actions WHERE person_id=?) "
                    "AND NOT EXISTS(SELECT 1 FROM fines WHERE person_id=?) AND NOT EXISTS(SELECT 1 FROM refusals WHERE person_id=?) "
                    "AND NOT EXISTS(SELECT 1 FROM receipts WHERE person_id=?)", (old_person,) * 5,
                )
        # Database changes commit together. Locked output files use the existing retry queue.
        return self._refresh_corrected_outputs(int(row["shift_id"]), affected_lists)

    def delete_fine(self, fine_id: int, *, expected_entry: FineEntry | None = None) -> PendingResult:
        affected_lists: set[int] = set()
        with self.db.write() as con:
            row = con.execute(
                "SELECT f.*,p.surname,p.given_name,p.birth_date FROM fines f "
                "JOIN people p ON p.id=f.person_id WHERE f.id=?", (fine_id,)
            ).fetchone()
            if not row:
                raise ValueError("Δεν βρέθηκε η επιλεγμένη πράξη.")
            if expected_entry is not None and self._row_to_entry(row, for_report=False) != expected_entry:
                raise ValueError("Η πράξη άλλαξε από άλλον σταθμό. Πατήστε ΑΝΑΝΕΩΣΗ και επιλέξτε την ξανά.")
            action = con.execute("SELECT id FROM actions WHERE id=?", (row["action_id"],)).fetchone()
            if not action:
                raise ValueError("Δεν βρέθηκε η συνδεδεμένη πράξη στο ιστορικό.")
            receipts = con.execute(
                "SELECT id,receipt_list_id FROM receipts WHERE action_id=?", (row["action_id"],)
            ).fetchall()
            if row["operation_type"] == "PAYMENT" and len(receipts) != 1:
                raise ValueError("Η είσπραξη δεν έχει μοναδική συνδεδεμένη εγγραφή στη Λίστα Εισπράξεων.")
            affected_lists.update(int(x["receipt_list_id"]) for x in receipts)
            shift_id = int(row["shift_id"])
            person_id = int(row["person_id"])
            con.execute("DELETE FROM receipts WHERE action_id=?", (row["action_id"],))
            con.execute("DELETE FROM fines WHERE id=?", (fine_id,))
            con.execute("DELETE FROM actions WHERE id=?", (row["action_id"],))
            con.execute(
                "DELETE FROM people WHERE id=? AND NOT EXISTS(SELECT 1 FROM actions WHERE person_id=?) "
                "AND NOT EXISTS(SELECT 1 FROM fines WHERE person_id=?) AND NOT EXISTS(SELECT 1 FROM refusals WHERE person_id=?) "
                "AND NOT EXISTS(SELECT 1 FROM receipts WHERE person_id=?)", (person_id,) * 5,
            )
        return self._refresh_corrected_outputs(shift_id, affected_lists)

    def _refresh_corrected_outputs(self, shift_id: int, affected_lists: set[int]) -> PendingResult:
        pending = PendingService(self.db, self, None, DailyActivityService(self.db))
        jobs = [f"RECEIPT_LIST:{list_id}" for list_id in sorted(affected_lists)]
        if self.db.get_shift(shift_id)["status"] == "CLOSED":
            jobs += [FINES_REPORT, DAILY_ACTIVITY]
        if (preview_root() / f"ΠΡΟΕΠΙΣΚΟΠΗΣΗ_ΠΡΟΣΤΙΜΩΝ_ΒΑΡΔΙΑ_{shift_id}.docx").exists():
            jobs.append("FINES_PREVIEW")
        if (preview_root() / f"ΗΜΕΡΗΣΙΑ_ΒΑΡΔΙΑ_{shift_id}.xlsx").exists():
            jobs.append("DAILY_PREVIEW")
        result = PendingResult([], [])
        for job_type in jobs:
            try:
                pending._run(job_type, shift_id)
                for job in self.db.list_pending_jobs():
                    if int(job["shift_id"]) == shift_id and job["job_type"] == job_type:
                        self.db.resolve_pending_job(int(job["id"]))
                result.completed.append(job_type)
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                self.db.add_pending_job(shift_id, job_type, message)
                result.failed.append((job_type, message))
        return result


    def search_fines(self, query: str = "", operation_type: str = "", limit: int = 300):
        q = normalize_text(query) if query.strip() else ""
        sql = """
        SELECT f.*,p.surname,p.given_name,p.birth_date,s.officer_name,s.started_at,s.ended_at
        FROM fines f
        JOIN people p ON p.id=f.person_id
        JOIN shifts s ON s.id=f.shift_id
        WHERE 1=1
        """
        args = []
        if q:
            like = f"%{q}%"
            raw = f"%{query.strip()}%"
            sql += " AND (p.surname_norm LIKE ? OR p.given_name_norm LIKE ? OR COALESCE(f.passport_no,'') LIKE ? " \
                   "OR COALESCE(f.imposition_protocol,'') LIKE ? OR COALESCE(f.collection_protocol,'') LIKE ?)"
            args += [like, like, raw, raw, raw]
        if operation_type in {"IMPOSITION", "PAYMENT"}:
            sql += " AND f.operation_type=?"
            args.append(operation_type)
        sql += " ORDER BY f.occurred_at DESC,f.id DESC LIMIT ?"
        args.append(int(limit))
        with self.db.connect() as con:
            return con.execute(sql, args).fetchall()

    @staticmethod
    def _row_to_entry(row, *, for_report: bool = True) -> FineEntry:
        method = row["collection_method"] or ""
        paravolo = row["paravolo"] or ""
        birth_date = row["birth_date"] or ""
        # People are stored canonically as YYYY-MM-DD for reliable search/matching,
        # while the established Word report expects DD/MM/YYYY.
        if birth_date:
            try:
                birth_date = datetime.strptime(birth_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                pass
        if for_report and row["operation_type"] == "PAYMENT" and not method and not paravolo:
            # The old report engine detects payment from paravolo/method. Keep the user-visible field blank
            # in storage but supply the established fallback only while generating the report.
            method = "EISPRAXI"
        return FineEntry(
            date=row["fine_date"],
            imposition_protocol=row["imposition_protocol"] or "",
            paravolo=paravolo,
            surname=row["surname"] or "",
            name=row["given_name"] or "",
            birth_date=birth_date,
            nationality=row["nationality"] or "",
            passport=row["passport_no"] or "",
            measure=row["measure"] or "",
            amount=int(row["amount"]),
            collection_method=method,
            collection_protocol=row["collection_protocol"] or "",
            responsible=row["responsible"] or "",
        )

    def generate_shift_report(self, shift_id: int, end_dt: datetime | None = None, *, archive: bool = False) -> Path | None:
        shift = self.db.get_shift(shift_id)
        if not shift:
            raise ValueError("Δεν βρέθηκε η βάρδια.")
        rows = self.fines_for_shift(shift_id)
        start_dt = datetime.fromisoformat(shift["started_at"])
        if shift["ended_at"]:
            final_end = datetime.fromisoformat(shift["ended_at"])
        else:
            final_end = end_dt or datetime.now()
        if final_end < start_dt:
            raise ValueError("Η ώρα λήξης είναι πριν από την αποθηκευμένη έναρξη της βάρδιας.")
        if archive:
            day = start_dt.strftime("%d-%m-%Y")
            folder = archive_root() / "ΠΡΟΣΤΙΜΑ" / f"{start_dt:%Y}" / f"{start_dt:%m}"
            folder.mkdir(parents=True, exist_ok=True)
            output = folder / f"ΑΝΑΦΟΡΑ ΠΡΟΣΤΙΜΩΝ {day} - ΒΑΡΔΙΑ {shift_id}.docx"
        else:
            output = preview_root() / f"ΠΡΟΕΠΙΣΚΟΠΗΣΗ_ΠΡΟΣΤΙΜΩΝ_ΒΑΡΔΙΑ_{shift_id}.docx"
        if not rows:
            with self.db.lock.acquire():
                output.unlink(missing_ok=True)
            return None
        with self.db.lock.acquire():
            header_tmp = output.with_suffix(".header.docx")
            try:
                self.engine.create_report_window(
                    header_tmp,
                    officer_name=shift["officer_name"],
                    officer_agms=shift["officer_agms"] or "",
                    start_dt=start_dt,
                    end_dt=final_end,
                    officer_rank_short=shift["officer_rank_short"] or "Ανθ/μου",
                    officer_rank_full=shift["officer_rank_full"] or "ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ",
                    electronically_signed=bool(shift["ended_at"]),
                    active=not bool(shift["ended_at"]),
                    signed_at=datetime.fromisoformat(shift["ended_at"]) if shift["ended_at"] else None,
                )
                self.engine.write_entries(output, [self._row_to_entry(x) for x in rows], source_docx=header_tmp)
            finally:
                header_tmp.unlink(missing_ok=True)
        return output

    @staticmethod
    def open_preview(path: str | Path) -> None:
        if os.name != "nt":
            return
        os.startfile(str(path))
