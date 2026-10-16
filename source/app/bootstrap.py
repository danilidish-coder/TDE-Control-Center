"""Create the existing services in their original order, outside the UI shell."""
from dataclasses import dataclass
from app.core.db import Database
from app.core.paths import db_path
from app.infrastructure.backup import backup_database
from app.features.receipts.service import ReceiptService
from app.features.fines.service import FineService
from app.features.refusals.service import RefusalService
from app.features.daily_activity.service import DailyActivityService
from app.features.periodicals.service import PeriodicalsService
from app.features.reports.pending import PendingService


@dataclass(frozen=True)
class ApplicationServices:
    db: Database
    receipts: ReceiptService
    fines: FineService
    refusals: RefusalService
    daily: DailyActivityService
    periodicals: PeriodicalsService
    pending: PendingService


def create_services() -> ApplicationServices:
    db = Database()
    backup_database(db_path())
    receipts = ReceiptService(db)
    fines = FineService(db)
    refusals = RefusalService(db)
    daily = DailyActivityService(db)
    periodicals = PeriodicalsService()
    pending = PendingService(db, fines, refusals, daily)
    return ApplicationServices(db, receipts, fines, refusals, daily, periodicals, pending)
