from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from app.shared.documents.common import GREEK_MONTHS, clean

PROFILE_AS_IS = "ΩΣ ΕΧΕΙ"
PROFILE_SAME_FOLDER = "ΤΕΛΕΥΤΑΙΟ ΣΤΟΝ ΙΔΙΟ ΦΑΚΕΛΟ"
PROFILE_DAILY_FOLDER = "ΗΜΕΡΗΣΙΟΣ ΦΑΚΕΛΟΣ"


@dataclass
class Package:
    id: str
    name: str
    system: str = ""
    to: str = ""
    cc: str = ""
    notes: str = ""
    root: str = ""
    active: bool = True
    order: int = 0
    last_folder: str = ""


@dataclass
class PackageFile:
    package_id: str
    name: str
    source_path: str
    active: bool = True
    profile: str = PROFILE_AS_IS
    name_template: str = ""
    prepared_path: str = ""
    prepared_date: str = ""
    archive_root: str = ""
    status: str = ""
    folder_layout: str = ""
    managed_copy_path: str = ""


@dataclass
class PreparationResult:
    package_id: str
    target_date: date
    prepared: list[Path]
    skipped_existing: list[Path]
    failed: list[str]
    already_current: bool = False


class IncompletePackageError(RuntimeError):
    """Mirrors the VBA Abort/Retry/Ignore prompt for a partially synced package."""
    def __init__(self, package_name: str, folder: Path, copied: int, active: int, missing: list[str], failed: list[str]):
        self.package_name = package_name
        self.folder = Path(folder)
        self.copied = int(copied)
        self.active = int(active)
        self.missing = list(missing)
        self.failed = list(failed)
        parts=[]
        if self.missing: parts.append("Δεν βρέθηκαν: " + ", ".join(self.missing))
        if self.failed: parts.append("Δεν αντιγράφηκαν μετά από 3 προσπάθειες: " + ", ".join(self.failed))
        super().__init__("Το πακέτο δεν ενημερώθηκε πλήρως. " + " | ".join(parts))


def build_month_folder(root: str | Path, d: date) -> Path:
    # Exact VBA: CStr(Month(targetDate)) -- NOT zero padded.
    return Path(root) / str(d.year) / f"{d.month}. {GREEK_MONTHS[d.month]} {d.year}"


def build_daily_folder(root: str | Path, d: date) -> Path:
    return build_month_folder(root, d) / d.strftime("%d-%m-%Y")


def contains_date_pattern(name: str) -> bool:
    return bool(re.search(r"\d{4}[-_]\d{2}[-_]\d{2}|\d{2}[-_]\d{2}[-_]\d{4}|\d{2}-\d{2}-\d{2}", name))


def extract_date_from_text(text: str) -> date | None:
    for pat, order in (
        (r"(\d{4})[-_](\d{2})[-_](\d{2})", "ymd"),
        (r"(\d{2})[-_](\d{2})[-_](\d{4})", "dmy"),
        (r"(\d{2})[-_](\d{2})[-_](\d{2})", "dmy2"),
    ):
        m = re.search(pat, text)
        if not m:
            continue
        try:
            a, b, c = (int(x) for x in m.groups())
            if order == "ymd":
                return date(a, b, c)
            if order == "dmy":
                return date(c, b, a)
            return date(2000 + c, b, a)
        except ValueError:
            return None
    return None


def build_name_template(name: str) -> str:
    result = name
    subs = [
        (r"\d{4}_\d{2}_\d{2}", "{YYYY_MM_DD}"),
        (r"\d{4}-\d{2}-\d{2}", "{YYYY-MM-DD}"),
        (r"\d{2}_\d{2}_\d{4}", "{DD_MM_YYYY}"),
        (r"\d{2}-\d{2}-\d{4}", "{DD-MM-YYYY}"),
        (r"\d{2}-\d{2}-\d{2}", "{DD-MM-YY}"),
    ]
    for pat, repl in subs:
        result = re.sub(pat, repl, result, count=1)
    if "{" not in result:
        p = Path(result)
        result = f"{p.stem} {{DD-MM-YYYY}}{p.suffix}"
    return result


def apply_name_template(template: str, d: date) -> str:
    return (
        template.replace("{YYYY_MM_DD}", d.strftime("%Y_%m_%d"))
        .replace("{YYYY-MM-DD}", d.strftime("%Y-%m-%d"))
        .replace("{DD_MM_YYYY}", d.strftime("%d_%m_%Y"))
        .replace("{DD-MM-YYYY}", d.strftime("%d-%m-%Y"))
        .replace("{DD-MM-YY}", d.strftime("%d-%m-%y"))
    )


def _parse_stored_date(raw: str) -> date | None:
    raw = clean(raw)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return date.fromisoformat(raw) if fmt == "%Y-%m-%d" else __import__('datetime').datetime.strptime(raw, fmt).date()
        except (ValueError, TypeError):
            pass
    return None


class PeriodicalsEngine:
    """Autonomous port of the v10.3 dynamic-package/periodical philosophy.

    The VBA remains the behavioral specification: non-periodic AS-IS files do not
    advance package date; dated files advance one calendar day from the oldest
    active file; existing target files are reused, not recreated; package sync
    removes only copies that this app manages, never original source files.
    """

    def __init__(self, packages: Iterable[Package], files: Iterable[PackageFile]):
        self.packages = {p.id: p for p in packages}
        self.package_cycles: dict[str, str] = {}
        self.files = list(files)

    def active_packages(self) -> list[Package]:
        return sorted(
            (p for p in self.packages.values() if p.active and clean(p.name)),
            key=lambda x: x.order,
        )

    def package_files(self, package_id: str, *, active_only: bool = True) -> list[PackageFile]:
        rows = [f for f in self.files if f.package_id == package_id]
        return [f for f in rows if f.active] if active_only else rows

    # -------------------- Simplified package management --------------------
    def _next_package_id(self) -> str:
        used = {clean(x).upper() for x in self.packages}
        n = 1
        while True:
            candidate = f"PKG{n:03d}"
            if candidate not in used:
                return candidate
            n += 1

    def _default_package_root(self) -> str:
        # v10.3 uses one common package root in normal operation. Reuse an
        # existing configured root instead of inventing a new location.
        for p in self.active_packages():
            if clean(p.root):
                return p.root
        for p in self.packages.values():
            if clean(p.root):
                return p.root
        return ""

    def create_package(self, name: str, *, root: str = "") -> Package:
        name = clean(name)
        if not name:
            raise ValueError("Το όνομα πακέτου δεν μπορεί να είναι κενό.")
        if any(ch in name for ch in '<>:"/\\|?*'):
            raise ValueError("Το όνομα πακέτου περιέχει μη επιτρεπτό χαρακτήρα.")
        if any(clean(p.name).casefold() == name.casefold() and p.active for p in self.packages.values()):
            raise ValueError("Υπάρχει ήδη ενεργό πακέτο με αυτό το όνομα.")
        pkg = Package(
            id=self._next_package_id(), name=name, root=clean(root) or self._default_package_root(),
            active=True, order=max((p.order for p in self.packages.values()), default=0) + 1,
        )
        self.packages[pkg.id] = pkg
        return pkg

    def rename_package(self, package_id: str, new_name: str) -> Package:
        if package_id not in self.packages:
            raise KeyError(package_id)
        new_name = clean(new_name)
        if not new_name:
            raise ValueError("Το νέο όνομα πακέτου δεν μπορεί να είναι κενό.")
        if any(ch in new_name for ch in '<>:"/\\|?*'):
            raise ValueError("Το όνομα πακέτου περιέχει μη επιτρεπτό χαρακτήρα.")
        if any(pid != package_id and p.active and clean(p.name).casefold() == new_name.casefold() for pid,p in self.packages.items()):
            raise ValueError("Υπάρχει ήδη ενεργό πακέτο με αυτό το όνομα.")
        pkg = self.packages[package_id]
        if clean(pkg.name) == new_name:
            return pkg
        pkg.name = new_name
        # Never delete/rename the old physical folder. A later sync creates/uses
        # the folder for the new package name, leaving historical copies intact.
        pkg.last_folder = ""
        for f in self.package_files(package_id, active_only=False):
            f.managed_copy_path = ""
        return pkg

    def delete_package(self, package_id: str) -> None:
        if package_id not in self.packages:
            raise KeyError(package_id)
        # Mirror v10.3: deactivate definitions only. No source file or previous
        # physical package folder is deleted.
        self.packages[package_id].active = False
        for f in self.package_files(package_id, active_only=False):
            f.active = False

    def catalog_files(self) -> list[PackageFile]:
        """Unique known periodicals across all packages, keyed by source path.

        This is only a catalogue for package membership. The original source is
        never changed.
        """
        out: list[PackageFile] = []
        seen: set[str] = set()
        for f in self.files:
            key = clean(f.source_path).casefold() or clean(f.name).casefold()
            if not key or key in seen:
                continue
            seen.add(key); out.append(f)
        return sorted(out, key=lambda x: clean(x.name).casefold())

    def add_known_file_to_package(self, package_id: str, source_path: str) -> PackageFile:
        if package_id not in self.packages or not self.packages[package_id].active:
            raise ValueError("Δεν υπάρχει ενεργό πακέτο.")
        key = clean(source_path).casefold()
        if not key:
            raise ValueError("Δεν έχει οριστεί αρχείο περιοδικού.")
        # Reactivate an old row in the same package first.
        for f in self.package_files(package_id, active_only=False):
            if clean(f.source_path).casefold() == key:
                f.active = True
                return f
        source = next((f for f in self.catalog_files() if clean(f.source_path).casefold() == key), None)
        if source is None:
            raise FileNotFoundError("Το περιοδικό δεν υπάρχει στον γνωστό κατάλογο.")
        clone = PackageFile(
            package_id=package_id, name=source.name, source_path=source.source_path, active=True,
            profile=source.profile, name_template=source.name_template, prepared_path=source.prepared_path,
            prepared_date=source.prepared_date, archive_root=source.archive_root, status=source.status,
            folder_layout=source.folder_layout, managed_copy_path="",
        )
        self.files.append(clone)
        return clone

    @staticmethod
    def _infer_archive_root(source: Path, profile: str) -> tuple[str, str]:
        profile = clean(profile).upper()
        if profile == PROFILE_AS_IS:
            return "", "AS_IS"
        if profile == PROFILE_SAME_FOLDER:
            # Expected BAT path: ROOT / YYYY / MONTH / FILE
            if len(source.parents) >= 3 and source.parent.parent.name.isdigit() and len(source.parent.parent.name) == 4:
                return str(source.parent.parent.parent), "BAT_MONTH"
            raise ValueError("Το αρχείο δεν βρίσκεται σε δομή ROOT\\ΕΤΟΣ\\ΜΗΝΑΣ όπως τα υπάρχοντα BAT.")
        if profile == PROFILE_DAILY_FOLDER:
            # Expected BAT path: ROOT / YYYY / MONTH / DD-MM-YYYY / FILE
            if len(source.parents) >= 4 and source.parent.parent.parent.name.isdigit() and len(source.parent.parent.parent.name) == 4:
                return str(source.parent.parent.parent.parent), "BAT_DAILY"
            raise ValueError("Το αρχείο δεν βρίσκεται σε δομή ROOT\\ΕΤΟΣ\\ΜΗΝΑΣ\\ΗΜΕΡΑ όπως τα υπάρχοντα BAT.")
        raise ValueError("Άγνωστος τρόπος προετοιμασίας περιοδικού.")

    def add_new_file_to_package(self, package_id: str, source_path: str, profile: str) -> PackageFile:
        if package_id not in self.packages or not self.packages[package_id].active:
            raise ValueError("Δεν υπάρχει ενεργό πακέτο.")
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        key = str(source).casefold()
        for f in self.package_files(package_id, active_only=False):
            if clean(f.source_path).casefold() == key:
                f.active = True
                return f
        archive_root, layout = self._infer_archive_root(source, profile)
        f = PackageFile(
            package_id=package_id, name=source.name, source_path=str(source), active=True,
            profile=profile, name_template=build_name_template(source.name), prepared_path="", prepared_date="",
            archive_root=archive_root, status="", folder_layout=layout, managed_copy_path="",
        )
        self.files.append(f)
        return f

    def remove_file_from_package(self, package_id: str, source_path: str) -> None:
        if package_id not in self.packages:
            raise KeyError(package_id)
        key = clean(source_path).casefold()
        found = False
        for f in self.package_files(package_id, active_only=False):
            if clean(f.source_path).casefold() == key and f.active:
                found = True
                # Deactivate the package membership, retain edited/unsent copies.
                f.active = False
        if not found:
            raise ValueError("Το περιοδικό δεν είναι ενεργό στο συγκεκριμένο πακέτο.")

    @staticmethod
    def _profile(f: PackageFile) -> str:
        return clean(f.profile).upper() or PROFILE_AS_IS

    def expected_prepared_path(self, f: PackageFile, d: date) -> Path | None:
        profile = self._profile(f)
        source = Path(f.source_path)
        template = f.name_template or build_name_template(source.name or f.name)
        archive = Path(f.archive_root) if clean(f.archive_root) else None

        if profile == PROFILE_AS_IS:
            return source
        if archive is None:
            return None
        if profile == PROFILE_SAME_FOLDER:
            folder = build_month_folder(archive, d) if clean(f.folder_layout).upper() == "BAT_MONTH" else archive
            return folder / apply_name_template(template, d)
        if profile == PROFILE_DAILY_FOLDER:
            folder = build_daily_folder(archive, d) if clean(f.folder_layout).upper() == "BAT_DAILY" else archive / d.strftime("%d-%m-%Y")
            return folder / apply_name_template(template, d)
        return None

    def latest_existing_prepared(self, f: PackageFile, allowed_date: date) -> tuple[date | None, Path | None]:
        """Port of LatestExistingPreparedDateForRow: use BAT date, not mtime."""
        if self._profile(f) == PROFILE_AS_IS:
            src = Path(f.source_path)
            return (allowed_date, src) if src.is_file() else (None, None)

        stored = _parse_stored_date(f.prepared_date)
        source_date = extract_date_from_text(Path(f.source_path).name)
        if stored and stored <= allowed_date:
            start = stored
        elif source_date and source_date <= allowed_date:
            start = source_date
        else:
            start = allowed_date - timedelta(days=366)

        latest_date: date | None = None
        latest_path: Path | None = None
        d = start
        while d <= allowed_date:
            candidate = self.expected_prepared_path(f, d)
            if candidate is not None and candidate.is_file():
                latest_date, latest_path = d, candidate
            d += timedelta(days=1)

        # VBA fallback: if the broad scan found nothing, also respect a valid
        # stored prepared path/date or the dated source path itself.
        if latest_date is None:
            pp = Path(f.prepared_path) if clean(f.prepared_path) else None
            if pp is not None and pp.is_file() and stored and stored <= allowed_date:
                latest_date, latest_path = stored, pp
            else:
                src = Path(f.source_path)
                if src.is_file() and source_date and source_date <= allowed_date:
                    latest_date, latest_path = source_date, src

        return latest_date, latest_path

    def package_next_prepared_date(self, package_id: str, allowed_date: date) -> date:
        has_periodic = False
        min_date: date | None = None
        for f in self.package_files(package_id):
            if self._profile(f) == PROFILE_AS_IS:
                continue
            has_periodic = True
            d, latest = self.latest_existing_prepared(f, allowed_date)
            if d is not None and latest is not None:
                f.prepared_path = str(latest)
                f.prepared_date = d.isoformat()
                f.status = "ΕΤΟΙΜΟ"
                if min_date is None or d < min_date:
                    min_date = d
        if not has_periodic or min_date is None:
            return allowed_date
        return min_date + timedelta(days=1)

    def prepare_file(self, f: PackageFile, target_date: date) -> tuple[Path | None, bool]:
        """Return (path, created_new). Existing target is marked ready and reused."""
        source = Path(f.source_path)
        profile = self._profile(f)
        target = self.expected_prepared_path(f, target_date)
        if target is None:
            return None, False

        if profile == PROFILE_AS_IS:
            if not source.is_file():
                return None, False
            f.prepared_path = str(source)
            f.prepared_date = target_date.isoformat()
            f.status = "ΕΤΟΙΜΟ"
            return source, False

        # Exact v10 behavior: if today's corresponding file already exists,
        # do not copy/open/recreate it; simply register it as ready.
        if target.is_file():
            f.prepared_path = str(target)
            f.prepared_date = target_date.isoformat()
            f.status = "ΕΤΟΙΜΟ"
            return target, False

        previous = target_date - timedelta(days=1)
        src = self.expected_prepared_path(f, previous)
        if src is None or not src.is_file():
            return None, False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        f.prepared_path = str(target)
        f.prepared_date = target_date.isoformat()
        f.status = "ΕΤΟΙΜΟ"
        return target, True

    def prepare_package(self, package_id: str, target_date: date) -> list[Path]:
        result: list[Path] = []
        for f in self.package_files(package_id):
            p, _ = self.prepare_file(f, target_date)
            if p is not None:
                result.append(p)
        return result

    def prepare_next_package(self, package_id: str, allowed_date: date) -> PreparationResult:
        target = self.package_next_prepared_date(package_id, allowed_date)
        if target > allowed_date:
            return PreparationResult(package_id, target, [], [], [], already_current=True)

        prepared: list[Path] = []
        skipped: list[Path] = []
        failed: list[str] = []
        seen_sources: set[str] = set()
        for f in self.package_files(package_id):
            # VBA package rows can point to the same actual source from multiple
            # packages; within one package only process a source once.
            key = clean(f.source_path).upper()
            if key and key in seen_sources:
                continue
            if key:
                seen_sources.add(key)
            expected = self.expected_prepared_path(f, target)
            existed = bool(expected and expected.is_file())
            p, created = self.prepare_file(f, target)
            if p is None:
                failed.append(f.name or Path(f.source_path).name)
            elif existed or not created:
                skipped.append(p)
            else:
                prepared.append(p)
        return PreparationResult(package_id, target, prepared, skipped, failed, already_current=False)

    def latest_prepared_path(self, f: PackageFile, allowed_date: date | None = None) -> Path | None:
        if self._profile(f) == PROFILE_AS_IS:
            p = Path(f.source_path)
            return p if p.is_file() else None
        if clean(f.prepared_path):
            p = Path(f.prepared_path)
            if p.is_file():
                return p
        if allowed_date is not None:
            d, p = self.latest_existing_prepared(f, allowed_date)
            if d is not None and p is not None:
                f.prepared_date = d.isoformat(); f.prepared_path = str(p); f.status = "ΕΤΟΙΜΟ"
                return p
        return None

    @staticmethod
    def _remove_managed_copy(f: PackageFile, destination_folder: Path) -> None:
        raw = clean(f.managed_copy_path)
        if not raw:
            return
        p = Path(raw)
        try:
            # Safety: delete only a copy inside this package folder.
            if p.is_file() and p.parent.resolve() == destination_folder.resolve():
                p.unlink()
        finally:
            f.managed_copy_path = ""

    @staticmethod
    def _copy_working_document(source: Path, destination: Path) -> None:
        created = False
        try:
            with destination.open("xb") as output:
                created = True
                with source.open("rb") as input_file:
                    shutil.copyfileobj(input_file, output)
            shutil.copystat(source, destination)
        except FileExistsError:
            # Another station may have created its working document meanwhile.
            return
        except Exception:
            if created:
                destination.unlink(missing_ok=True)
            raise

    def sync_package_folder(self, package_id: str, allowed_date: date | None = None) -> Path:
        """Mirror v10.3 SyncPackageFolder up to the user's Abort/Retry/Ignore choice.

        A partial package is left on disk exactly as in the VBA and reported through
        IncompletePackageError; the GUI then offers Retry / Ignore / Abort.
        """
        package = self.packages[package_id]
        if not clean(package.root):
            raise ValueError("Δεν έχει οριστεί μόνιμος φάκελος πακέτου.")
        folder = Path(package.root) / package.name
        cycle_date = self.package_cycles.get(package_id, "")
        if cycle_date:
            # Step 1 chooses the next cycle. Earlier unsent/edited packages stay
            # exactly where they were; Step 3 never deletes or rolls a cycle.
            folder = folder / date.fromisoformat(cycle_date).isoformat()
        folder.mkdir(parents=True, exist_ok=True)

        copied = 0
        active = 0
        missing: list[str] = []
        failed: list[str] = []
        for f in self.package_files(package_id, active_only=False):
            if not f.active:
                continue
            active += 1
            src = self.latest_prepared_path(f, allowed_date)
            if src is None or not src.is_file():
                missing.append(f.name or Path(f.source_path).name)
                continue
            dest = folder / src.name
            # Earlier managed copies may be edited or unsent; retain them.

            copy_error: Exception | None = None
            if src.resolve() != dest.resolve() and not dest.exists():
                # Existing copies are operator working documents. Repeated
                # Step 3 is idempotent and must never overwrite their edits.
                for _attempt in range(3):
                    try:
                        self._copy_working_document(src, dest)
                        copy_error = None
                        break
                    except Exception as exc:
                        copy_error = exc
            if copy_error is not None:
                failed.append(f"{src.name} [{copy_error}]")
                continue

            f.managed_copy_path = str(dest)
            copied += 1

        package.last_folder = str(folder)
        if active == 0:
            raise ValueError(f"Το πακέτο «{package.name}» δεν περιέχει ενεργά αρχεία.")
        if missing or failed:
            raise IncompletePackageError(package.name, folder, copied, active, missing, failed)
        if copied == 0:
            raise FileNotFoundError("Δεν βρέθηκε ενημερωμένο αρχείο για αποστολή. Προηγείται η ενημέρωση αρχείων.")
        return folder

