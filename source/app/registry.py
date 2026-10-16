"""Explicit module registration. Definition order is the original page order."""
from app.contracts import ModuleDefinition
from app.features.fines.page import FinesPage
from app.features.refusals.page import RefusalsPage
from app.features.daily_activity.page import DailyActivityPage
from app.features.periodicals.page import PeriodicalsPage
from app.features.reports.page import ShiftReportsPage
from app.features.people.page import PersonArchivePage
from app.features.receipts.page import ReceiptsPage


DEFAULT_MODULES = (
    ModuleDefinition("fines", "ΠΡΟΣΤΙΜΑ", "skin_nav_fines.svg", lambda s: FinesPage(s.fines)),
    ModuleDefinition("refusals", "ΑΡΝΗΣΕΙΣ", "skin_refusals.svg", lambda s: RefusalsPage(s.refusals)),
    ModuleDefinition("daily", "ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ", "skin_nav_daily.svg", lambda s: DailyActivityPage(s.daily)),
    ModuleDefinition("periodics", "ΠΕΡΙΟΔΙΚΑ", "skin_periodics.svg", lambda s: PeriodicalsPage(s.periodicals)),
    ModuleDefinition("reports", None, None, lambda s: ShiftReportsPage(s.db, s.fines, s.refusals, s.daily)),
    ModuleDefinition("people", "ΑΡΧΕΙΟ - ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ", "skin_people.svg", lambda s: PersonArchivePage(s.db)),
    ModuleDefinition("receipts", "ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ", "skin_nav_receipts.svg", lambda s: ReceiptsPage(s.receipts)),
)
# Navigation order deliberately differs from page creation order.
NAVIGATION_KEYS = ("fines", "refusals", "daily", "periodics", "people", "receipts")


def validate_modules(modules):
    keys = [m.key for m in modules]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate module key")
    for module in modules:
        if module.title is not None and module.icon is None:
            raise ValueError(f"Missing navigation icon: {module.key}")


def navigation_modules(modules):
    by_key = {m.key: m for m in modules}
    ordered = [by_key[k] for k in NAVIGATION_KEYS if k in by_key]
    return ordered + [m for m in modules if m.title is not None and m.key not in NAVIGATION_KEYS]


def create_pages(services, modules):
    validate_modules(modules)
    return {m.key: m.create_page(services) for m in modules}
