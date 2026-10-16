"""Cross-module coordination; preserve the existing commit/archive/backup order."""
from app.core.paths import db_path
from app.infrastructure.backup import backup_database


class ApplicationWorkflow:
    def __init__(self, services):
        self.services = services

    def start_shift(self, officer_name, **identity):
        return self.services.db.start_shift(officer_name, **identity)

    def close_shift(self):
        shift_id = self.services.db.close_shift()
        result = self.services.pending.archive_shift(shift_id)
        backup_database(db_path())
        return shift_id, result
