from __future__ import annotations

import base64
import json
import os
from app.services.pdf_preview import open_document_preview
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.core.db import Database
from app.core.paths import archive_root, preview_root, resource_path, resolve_runtime_path
from app.core.textnorm import normalize_birth_date, normalize_text, phonetic_key
from app.docgen.common import fmt_date
from app.docgen.refusals import RefusalEntry, RefusalDocumentEngine, VasReportEngine
from app.services.daily_activity import DailyActivityService
from app.services.pending import DAILY_ACTIVITY, REFUSALS_VAS, PendingResult, PendingService


def _safe(value: str) -> str:
    value = (value or '').strip().upper()
    value = re.sub(r'[<>:"/\\|?*]+', '_', value)
    return value.strip(' .') or 'ΧΩΡΙΣ_ΟΝΟΜΑ'


class RefusalService:
    def __init__(self, db: Database):
        self.db = db
        self.individual_engine = RefusalDocumentEngine(resource_path('Master_Template_Arnisi.docx'))
        self.vas_engine = VasReportEngine(resource_path('VAS_base.docx'))

    def add_refusal(self, entry: RefusalEntry, occurred_at: datetime | None = None):
        entry.validate()
        shift = self.db.get_open_shift()
        if not shift:
            raise ValueError('Δεν υπάρχει ενεργή βάρδια. Πρώτα ΕΝΑΡΞΗ ΒΑΡΔΙΑΣ.')
        now_dt = occurred_at or datetime.now()
        now = now_dt.isoformat(timespec='seconds')

        # Build the individual document before committing data. If the template is bad,
        # no partial service act is written to the database.
        temp = preview_root() / f'.refusal_new_{os.getpid()}_{uuid.uuid4().hex}.docx'
        temp.unlink(missing_ok=True)
        self.individual_engine.create(temp, entry)

        try:
            sn, gn = normalize_text(entry.surname), normalize_text(entry.name)
            bd = normalize_birth_date(entry.birth_date)
            with self.db.write() as con:
                person = con.execute(
                    "SELECT id FROM people WHERE surname_norm=? AND given_name_norm=? "
                    "AND COALESCE(birth_date,'')=COALESCE(?, '') ORDER BY id LIMIT 1",
                    (sn, gn, bd),
                ).fetchone()
                if person:
                    person_id = int(person['id'])
                else:
                    cur = con.execute(
                        "INSERT INTO people(surname,given_name,birth_date,surname_norm,given_name_norm,"
                        "surname_phonetic,given_name_phonetic,created_at) VALUES(?,?,?,?,?,?,?,?)",
                        (entry.surname.strip(), entry.name.strip(), bd, sn, gn,
                         phonetic_key(entry.surname), phonetic_key(entry.name), now),
                    )
                    person_id = int(cur.lastrowid)

                details = {
                    'aa': entry.aa, 'year': entry.year,
                    'protocol_prefix': entry.protocol_prefix, 'protocol_no': entry.protocol_no,
                    'language': entry.language, 'birth_place': entry.birth_place,
                    'nationality': entry.nationality, 'residence': entry.residence,
                    'passport_issuer': entry.passport_issuer, 'origin_country': entry.origin_country,
                    'measure_country': entry.measure_country,
                    'measure_no': entry.measure_no, 'measure_from': entry.measure_from, 'measure_to': entry.measure_to,
                    'sis_country': entry.sis_country, 'sis_no': entry.sis_no,
                    'sis_from': entry.sis_from, 'sis_to': entry.sis_to,
                }
                action = con.execute(
                    "INSERT INTO actions(person_id,shift_id,action_type,reason,occurred_at,protocol_no,passport_no,details_json) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (person_id, int(shift['id']), 'REFUSAL', entry.reason.strip(), now,
                     entry.protocol_page2, entry.passport.strip(), json.dumps(details, ensure_ascii=False)),
                )
                action_id = int(action.lastrowid)
                cur = con.execute(
                    "INSERT INTO refusals(person_id,shift_id,action_id,occurred_at,aa,refusal_year,protocol_prefix,protocol_no,"
                    "refusal_date,refusal_time,sex,birth_date_display,passport_no,issue_date,reason,"
                    "measure_country,measure_no,measure_from,measure_to,sis_country,sis_no,sis_from,sis_to,language) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (person_id, int(shift['id']), action_id, now, entry.aa.strip(), entry.year.strip(),
                     entry.protocol_prefix.strip(), entry.protocol_no.strip(), fmt_date(entry.date, '-'), entry.time.strip(),
                     entry.sex.strip(), fmt_date(entry.birth_date, '-') if entry.birth_date.strip() else '',
                     entry.passport.strip(), fmt_date(entry.issue_date, '-') if entry.issue_date.strip() else '',
                     entry.reason.strip(), entry.measure_country.strip(), entry.measure_no.strip(),
                     fmt_date(entry.measure_from, '-') if entry.measure_from.strip() else '',
                     fmt_date(entry.measure_to, '-') if entry.measure_to.strip() else '',
                     entry.sis_country.strip(), entry.sis_no.strip(),
                     fmt_date(entry.sis_from, '-') if entry.sis_from.strip() else '',
                     fmt_date(entry.sis_to, '-') if entry.sis_to.strip() else '', entry.language.strip()),
                )
                refusal_id = int(cur.lastrowid)
                con.execute(
                    "UPDATE refusals SET birth_place=?,nationality=?,residence=?,passport_issuer=?,origin_country=? WHERE id=?",
                    (entry.birth_place.strip(), entry.nationality.strip(), entry.residence.strip(),
                     entry.passport_issuer.strip(), entry.origin_country.strip(), refusal_id),
                )

            latest = self.latest_refusal_path()
            latest.parent.mkdir(parents=True, exist_ok=True)
            # File operations are serialized too: multiple terminals may create refusals at once.
            # The highest committed refusal id owns the shared "latest" preview.
            with self.db.lock.acquire():
                archive = self._archive_individual(refusal_id, entry, temp, now_dt)
                with self.db.connect() as con:
                    max_id = int(con.execute('SELECT COALESCE(MAX(id),0) AS m FROM refusals').fetchone()['m'])
                if refusal_id == max_id:
                    latest_tmp = latest.with_suffix(f'.{os.getpid()}.tmp.docx')
                    shutil.copy2(temp, latest_tmp)
                    os.replace(latest_tmp, latest)
            with self.db.write() as con:
                con.execute('UPDATE refusals SET archive_path=? WHERE id=?', (str(archive), refusal_id))

            vas = self.generate_vas(int(shift['id']), end_dt=now_dt, archive=False)
            return refusal_id, latest, vas, archive
        finally:
            temp.unlink(missing_ok=True)

    def _archive_individual(self, refusal_id: int, entry: RefusalEntry, src: Path, when: datetime) -> Path:
        folder = archive_root() / 'ΑΡΝΗΣΕΙΣ' / f'{when:%Y}' / f'{when:%m}'
        folder.mkdir(parents=True, exist_ok=True)
        proto = _safe(f'{entry.protocol_prefix}-{entry.protocol_no}')
        surname = _safe(entry.surname)
        path = folder / f'ΑΡΝΗΣΗ_{when:%d-%m-%Y}_{refusal_id:04d}_{proto}_{surname}.docx'
        shutil.copy2(src, path)
        return path

    @staticmethod
    def latest_refusal_path() -> Path:
        return preview_root() / 'ΤΕΛΕΥΤΑΙΑ_ΑΡΝΗΣΗ.docx'

    def refusals_for_shift(self, shift_id: int):
        with self.db.connect() as con:
            return con.execute(
                "SELECT r.*,p.surname,p.given_name FROM refusals r JOIN people p ON p.id=r.person_id "
                "WHERE r.shift_id=? ORDER BY r.id", (shift_id,)
            ).fetchall()

    def get_refusal(self, refusal_id: int):
        with self.db.connect() as con:
            return con.execute(
                "SELECT r.*,p.surname,p.given_name,p.birth_date FROM refusals r "
                "JOIN people p ON p.id=r.person_id WHERE r.id=?", (refusal_id,)
            ).fetchone()

    def _corrected_person(self, con, row, entry: RefusalEntry) -> int:
        old_id = int(row["person_id"])
        bd = normalize_birth_date(entry.birth_date)
        old_person = con.execute("SELECT * FROM people WHERE id=?", (old_id,)).fetchone()
        if (old_person and normalize_text(old_person["surname"]) == normalize_text(entry.surname)
                and normalize_text(old_person["given_name"]) == normalize_text(entry.name)
                and (old_person["birth_date"] or "") == (bd or "")):
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
            "OR EXISTS(SELECT 1 FROM fines WHERE person_id=?) "
            "OR EXISTS(SELECT 1 FROM refusals WHERE person_id=? AND id<>?) "
            "OR EXISTS(SELECT 1 FROM receipts WHERE person_id=?)",
            (old_id, row["action_id"], old_id, old_id, row["id"], old_id),
        ).fetchone()[0]
        values = (
            entry.surname.strip(), entry.name.strip(), bd, sn, gn,
            phonetic_key(entry.surname), phonetic_key(entry.name),
        )
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

    @staticmethod
    def _details(entry: RefusalEntry) -> dict:
        return {
            "aa": entry.aa, "year": entry.year,
            "protocol_prefix": entry.protocol_prefix, "protocol_no": entry.protocol_no,
            "language": entry.language, "birth_place": entry.birth_place,
            "nationality": entry.nationality, "residence": entry.residence,
            "passport_issuer": entry.passport_issuer, "origin_country": entry.origin_country,
            "measure_country": entry.measure_country, "measure_no": entry.measure_no,
            "measure_from": entry.measure_from, "measure_to": entry.measure_to,
            "sis_country": entry.sis_country, "sis_no": entry.sis_no,
            "sis_from": entry.sis_from, "sis_to": entry.sis_to,
        }

    def update_refusal(self, refusal_id: int, entry: RefusalEntry, *, expected_entry: RefusalEntry | None = None) -> PendingResult:
        entry.validate()
        with self.db.write() as con:
            row = con.execute(
                "SELECT r.*,p.surname,p.given_name,p.birth_date FROM refusals r "
                "JOIN people p ON p.id=r.person_id WHERE r.id=?", (refusal_id,)
            ).fetchone()
            if not row:
                raise ValueError("Δεν βρέθηκε η επιλεγμένη άρνηση.")
            if expected_entry is not None and self._row_to_entry(row) != expected_entry:
                raise ValueError("Η άρνηση άλλαξε από άλλον σταθμό. Πατήστε ΑΝΑΝΕΩΣΗ και επιλέξτε την ξανά.")
            action = con.execute("SELECT * FROM actions WHERE id=?", (row["action_id"],)).fetchone()
            if not action:
                raise ValueError("Δεν βρέθηκε η συνδεδεμένη πράξη στο ιστορικό.")
            person_id = self._corrected_person(con, row, entry)
            con.execute(
                "UPDATE actions SET person_id=?,reason=?,protocol_no=?,passport_no=?,details_json=? WHERE id=?",
                (person_id, entry.reason.strip(), entry.protocol_page2, entry.passport.strip(),
                 json.dumps(self._details(entry), ensure_ascii=False), row["action_id"]),
            )
            con.execute(
                "UPDATE refusals SET person_id=?,aa=?,refusal_year=?,protocol_prefix=?,protocol_no=?,"
                "refusal_date=?,refusal_time=?,sex=?,birth_date_display=?,passport_no=?,issue_date=?,reason=?,"
                "measure_country=?,measure_no=?,measure_from=?,measure_to=?,sis_country=?,sis_no=?,sis_from=?,sis_to=?,"
                "language=?,birth_place=?,nationality=?,residence=?,passport_issuer=?,origin_country=? WHERE id=?",
                (
                    person_id, entry.aa.strip(), entry.year.strip(), entry.protocol_prefix.strip(), entry.protocol_no.strip(),
                    fmt_date(entry.date, "-"), entry.time.strip(), entry.sex.strip(),
                    fmt_date(entry.birth_date, "-") if entry.birth_date.strip() else "", entry.passport.strip(),
                    fmt_date(entry.issue_date, "-") if entry.issue_date.strip() else "", entry.reason.strip(),
                    entry.measure_country.strip(), entry.measure_no.strip(),
                    fmt_date(entry.measure_from, "-") if entry.measure_from.strip() else "",
                    fmt_date(entry.measure_to, "-") if entry.measure_to.strip() else "",
                    entry.sis_country.strip(), entry.sis_no.strip(),
                    fmt_date(entry.sis_from, "-") if entry.sis_from.strip() else "",
                    fmt_date(entry.sis_to, "-") if entry.sis_to.strip() else "", entry.language.strip(),
                    entry.birth_place.strip(), entry.nationality.strip(), entry.residence.strip(),
                    entry.passport_issuer.strip(), entry.origin_country.strip(), refusal_id,
                ),
            )
            shift_id = int(row["shift_id"])
            old_person = int(row["person_id"])
            if old_person != person_id:
                con.execute(
                    "DELETE FROM people WHERE id=? AND NOT EXISTS(SELECT 1 FROM actions WHERE person_id=?) "
                    "AND NOT EXISTS(SELECT 1 FROM fines WHERE person_id=?) AND NOT EXISTS(SELECT 1 FROM refusals WHERE person_id=?) "
                    "AND NOT EXISTS(SELECT 1 FROM receipts WHERE person_id=?)", (old_person,) * 5,
                )
        return self._refresh_corrected_outputs(shift_id, refusal_id=refusal_id)

    def delete_refusal(self, refusal_id: int, *, expected_entry: RefusalEntry | None = None) -> PendingResult:
        with self.db.write() as con:
            row = con.execute(
                "SELECT r.*,p.surname,p.given_name,p.birth_date FROM refusals r "
                "JOIN people p ON p.id=r.person_id WHERE r.id=?", (refusal_id,)
            ).fetchone()
            if not row:
                raise ValueError("Δεν βρέθηκε η επιλεγμένη άρνηση.")
            if expected_entry is not None and self._row_to_entry(row) != expected_entry:
                raise ValueError("Η άρνηση άλλαξε από άλλον σταθμό. Πατήστε ΑΝΑΝΕΩΣΗ και επιλέξτε την ξανά.")
            action = con.execute("SELECT id FROM actions WHERE id=?", (row["action_id"],)).fetchone()
            if not action:
                raise ValueError("Δεν βρέθηκε η συνδεδεμένη πράξη στο ιστορικό.")
            shift_id = int(row["shift_id"])
            person_id = int(row["person_id"])
            archive_path = str(row["archive_path"] or "")
            con.execute("DELETE FROM refusals WHERE id=?", (refusal_id,))
            con.execute("DELETE FROM actions WHERE id=?", (row["action_id"],))
            con.execute(
                "DELETE FROM people WHERE id=? AND NOT EXISTS(SELECT 1 FROM actions WHERE person_id=?) "
                "AND NOT EXISTS(SELECT 1 FROM fines WHERE person_id=?) AND NOT EXISTS(SELECT 1 FROM refusals WHERE person_id=?) "
                "AND NOT EXISTS(SELECT 1 FROM receipts WHERE person_id=?)", (person_id,) * 5,
            )
        return self._refresh_corrected_outputs(shift_id, deleted_archive_path=archive_path)

    def refresh_latest_preview(self) -> Path | None:
        with self.db.connect() as con:
            row = con.execute("SELECT id FROM refusals ORDER BY id DESC LIMIT 1").fetchone()
        latest = self.latest_refusal_path()
        if not row:
            latest.unlink(missing_ok=True)
            return None
        return self.generate_individual_from_id(int(row["id"]), preview=True)

    def _refresh_corrected_outputs(
        self, shift_id: int, *, refusal_id: int | None = None, deleted_archive_path: str = ""
    ) -> PendingResult:
        pending = PendingService(self.db, None, self, DailyActivityService(self.db))
        jobs: list[str] = []
        if refusal_id is not None:
            jobs.append(f"REFUSAL_INDIVIDUAL:{refusal_id}")
        if deleted_archive_path:
            encoded = base64.urlsafe_b64encode(deleted_archive_path.encode("utf-8")).decode("ascii")
            jobs.append(f"REFUSAL_FILE_DELETE:{encoded}")
        jobs.append("REFUSAL_LATEST")
        shift = self.db.get_shift(shift_id)
        if shift and shift["status"] == "CLOSED":
            jobs += [REFUSALS_VAS, DAILY_ACTIVITY]
        if (preview_root() / f"ΒΑΣ_ΒΑΡΔΙΑ_{shift_id}.docx").exists():
            jobs.append("REFUSALS_PREVIEW")
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

    @staticmethod
    def _row_to_entry(row) -> RefusalEntry:
        return RefusalEntry(
            aa=row['aa'] or '', year=row['refusal_year'] or '', protocol_prefix=row['protocol_prefix'] or '',
            protocol_no=row['protocol_no'] or '', date=row['refusal_date'] or '', time=row['refusal_time'] or '',
            sex=row['sex'] or '', surname=row['surname'] or '', name=row['given_name'] or '',
            birth_date=row['birth_date_display'] or '', passport=row['passport_no'] or '',
            issue_date=row['issue_date'] or '', reason=row['reason'] or '', measure_country=row['measure_country'] or '',
            measure_no=row['measure_no'] or '', measure_from=row['measure_from'] or '', measure_to=row['measure_to'] or '',
            sis_country=row['sis_country'] or '', sis_no=row['sis_no'] or '', sis_from=row['sis_from'] or '',
            sis_to=row['sis_to'] or '', language=row['language'] or 'ΑΛΒΑΝΙΚΑ',
            birth_place=row['birth_place'] or '', nationality=row['nationality'] or '',
            residence=row['residence'] or '', passport_issuer=row['passport_issuer'] or '',
            origin_country=row['origin_country'] or ''
        )

    def generate_vas(self, shift_id: int, end_dt: datetime | None = None, *, archive: bool = False) -> Path | None:
        with self.db.lock.acquire():
            shift = self.db.get_shift(shift_id)
            if not shift:
                raise ValueError('Δεν βρέθηκε η βάρδια.')
            start = datetime.fromisoformat(shift['started_at'])
            if archive:
                folder = archive_root() / 'ΑΡΝΗΣΕΙΣ' / f'{start:%Y}' / f'{start:%m}'
                output = folder / f'ΒΑΣ_{start:%d-%m-%Y}_ΒΑΡΔΙΑ_{shift_id}.docx'
            else:
                output = preview_root() / f'ΒΑΣ_ΒΑΡΔΙΑ_{shift_id}.docx'
            rows = self.refusals_for_shift(shift_id)
            if not rows:
                output.unlink(missing_ok=True)
                return None
            if shift['ended_at']:
                end = datetime.fromisoformat(shift['ended_at'])
            else:
                end = end_dt or datetime.now()
            if end <= start:
                end = start
            output.parent.mkdir(parents=True, exist_ok=True)
            self.vas_engine.create(
                output, [self._row_to_entry(r) for r in rows],
                start.strftime('%d-%m-%Y'), end.strftime('%d-%m-%Y'),
                start_time=start.strftime('%H:%M'), end_time=end.strftime('%H:%M'),
                officer_name=shift['officer_name'] or '',
                officer_rank=shift['officer_rank_full'] or shift['officer_rank_short'] or '',
                officer_agms=shift['officer_agms'] or '',
                signed_at=(datetime.fromisoformat(shift['ended_at']).strftime('%d/%m/%Y %H:%M') if shift['ended_at'] else '')
            )
            return output

    def search_refusals(self, query: str = '', reason: str = '', limit: int = 300):
        q = normalize_text(query) if query.strip() else ''
        sql = """
        SELECT r.*,p.surname,p.given_name,s.officer_name,s.started_at,s.ended_at
        FROM refusals r
        JOIN people p ON p.id=r.person_id
        JOIN shifts s ON s.id=r.shift_id
        WHERE 1=1
        """
        args = []
        if q:
            like = f'%{q}%'; raw = f'%{query.strip()}%'
            sql += " AND (p.surname_norm LIKE ? OR p.given_name_norm LIKE ? OR COALESCE(r.passport_no,'') LIKE ? OR COALESCE(r.protocol_no,'') LIKE ?)"
            args += [like, like, raw, raw]
        if reason.strip():
            sql += ' AND r.reason=?'; args.append(reason.strip())
        sql += ' ORDER BY r.occurred_at DESC,r.id DESC LIMIT ?'; args.append(int(limit))
        with self.db.connect() as con:
            return con.execute(sql, args).fetchall()

    def generate_individual_from_id(self, refusal_id: int, *, preview: bool = True) -> Path:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT r.*,p.surname,p.given_name FROM refusals r JOIN people p ON p.id=r.person_id WHERE r.id=?",
                (refusal_id,),
            ).fetchone()
        if not row:
            raise ValueError('Δεν βρέθηκε η άρνηση.')
        output = self.latest_refusal_path() if preview else resolve_runtime_path(row['archive_path'])
        self.individual_engine.create(output, self._row_to_entry(row))
        return output

    @staticmethod
    def open_file(path: str | Path) -> None:
        if os.name == 'nt':
            open_document_preview(resolve_runtime_path(path))
