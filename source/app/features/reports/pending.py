from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from app.core.db import Database
from app.core.paths import resolve_runtime_path


FINES_REPORT = "FINES_REPORT"
REFUSALS_VAS = "REFUSALS_VAS"
DAILY_ACTIVITY = "DAILY_ACTIVITY"
REFUSALS_PREVIEW = "REFUSALS_PREVIEW"
REFUSAL_LATEST = "REFUSAL_LATEST"

LABELS = {
    FINES_REPORT: "Αναφορά Προστίμων",
    REFUSALS_VAS: "ΒΑΣ Αρνήσεων",
    DAILY_ACTIVITY: "Ημερήσια Δραστηριότητα",
}


@dataclass
class PendingResult:
    completed: list[str]
    failed: list[tuple[str, str]]


class PendingService:
    """Queues only real failed archive generations and retries exactly those jobs."""

    def __init__(self, db: Database, fines, refusals, daily):
        self.db = db
        self.fines = fines
        self.refusals = refusals
        self.daily = daily

    def _run(self, job_type: str, shift_id: int):
        if job_type == FINES_REPORT:
            return self.fines.generate_shift_report(shift_id, archive=True)
        if job_type == REFUSALS_VAS:
            return self.refusals.generate_vas(shift_id, archive=True)
        if job_type == DAILY_ACTIVITY:
            return self.daily.generate(shift_id, archive=True)
        if job_type == REFUSALS_PREVIEW:
            return self.refusals.generate_vas(shift_id, archive=False)
        if job_type == REFUSAL_LATEST:
            return self.refusals.refresh_latest_preview()
        if job_type.startswith("REFUSAL_INDIVIDUAL:"):
            return self.refusals.generate_individual_from_id(int(job_type.split(":", 1)[1]), preview=False)
        if job_type.startswith("REFUSAL_FILE_DELETE:"):
            raw = base64.urlsafe_b64decode(job_type.split(":", 1)[1].encode("ascii")).decode("utf-8")
            path = resolve_runtime_path(raw)
            path.unlink(missing_ok=True)
            return path
        if job_type == "FINES_PREVIEW":
            return self.fines.generate_shift_report(shift_id, archive=False)
        if job_type == "DAILY_PREVIEW":
            return self.daily.generate(shift_id, archive=False)
        if job_type.startswith("RECEIPT_LIST:"):
            from app.features.receipts.service import ReceiptService
            return ReceiptService(self.db).refresh_archived_list(int(job_type.split(":", 1)[1]))
        raise ValueError(f"Άγνωστη εκκρεμής ενημέρωση: {job_type}")

    def archive_shift(self, shift_id: int) -> PendingResult:
        completed: list[str] = []
        failed: list[tuple[str, str]] = []
        for job_type in (FINES_REPORT, REFUSALS_VAS, DAILY_ACTIVITY):
            try:
                self._run(job_type, shift_id)
                completed.append(job_type)
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                self.db.add_pending_job(shift_id, job_type, message)
                failed.append((job_type, message))
        return PendingResult(completed, failed)

    def retry_pending(self) -> PendingResult:
        completed: list[str] = []
        failed: list[tuple[str, str]] = []
        for row in self.db.list_pending_jobs():
            try:
                self._run(str(row["job_type"]), int(row["shift_id"]))
                self.db.resolve_pending_job(int(row["id"]))
                completed.append(str(row["job_type"]))
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                self.db.fail_pending_job(int(row["id"]), message)
                failed.append((str(row["job_type"]), message))
        return PendingResult(completed, failed)

    def count(self) -> int:
        return self.db.pending_count()

    @staticmethod
    def label(job_type: str) -> str:
        if job_type.startswith("RECEIPT_LIST:"):
            return "Λίστα Εισπράξεων " + job_type.split(":", 1)[1]
        if job_type == "FINES_PREVIEW":
            return "Προεπισκόπηση Προστίμων"
        if job_type == "DAILY_PREVIEW":
            return "Προεπισκόπηση Ημερήσιας Δραστηριότητας"
        if job_type == REFUSALS_PREVIEW:
            return "Προεπισκόπηση ΒΑΣ"
        if job_type == REFUSAL_LATEST:
            return "Τελευταία Άρνηση"
        if job_type.startswith("REFUSAL_INDIVIDUAL:"):
            return "Ατομική Άρνηση " + job_type.split(":", 1)[1]
        if job_type.startswith("REFUSAL_FILE_DELETE:"):
            return "Διαγραφή αρχείου ατομικής Άρνησης"
        return LABELS.get(job_type, job_type)
