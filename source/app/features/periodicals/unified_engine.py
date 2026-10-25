from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

from app.shared.documents.common import clean
from app.core.textnorm import normalize_text
from app.features.periodicals.engine import (
    PackageFile, PeriodicalsEngine, PreparationResult,
)
from app.features.periodicals.dates import (
    date_tokens, destination_folder, filename_date,
    replace_filename_date, series_folder_for_filename,
)

PROFILE_UNIFIED = "ΕΝΙΑΙΟ"
UNIFIED_LAYOUT = "YEAR_MONTH"


def _structured_root(source: Path) -> Path:
    parents = list(source.parents)
    if len(parents) >= 3 and parents[1].name.isdigit() and len(parents[1].name) == 4:
        return parents[2]
    if len(parents) >= 4 and parents[2].name.isdigit() and len(parents[2].name) == 4:
        return parents[3]
    return source.parent


def _series_name(filename: str) -> str:
    try:
        return series_folder_for_filename(filename)
    except ValueError:
        return ""


def _dated_name(name: str, d: date) -> str:
    try:
        return replace_filename_date(name, d)
    except ValueError:
        p = Path(name)
        return f"{p.stem} {d:%d-%m-%Y}{p.suffix}"


class UnifiedPeriodicalsEngine(PeriodicalsEngine):
    """Single-rule engine layered over the v1.0.12 package-management shell."""

    def __init__(self, packages, files):
        super().__init__(packages, files)
        self._normalize_definitions()

    @staticmethod
    def _scan_root(source: Path, root: Path) -> Path | None:
        for candidate in (root, *root.parents, *source.parents):
            if candidate.name.casefold() in {"1. scan folder reports", "scan folder"}:
                return candidate
        return None

    @staticmethod
    def _daily_root(root: Path) -> bool:
        name = normalize_text(root.name).replace(" ", "")
        return name in {"IMERISIAKINISI", "IMERHSIAKINISI", "HMERISIAKINISI"}

    def _normalize_file(self, f: PackageFile) -> None:
        source = Path(f.source_path) if clean(f.source_path) else Path(f.name)
        root = Path(f.archive_root) if clean(f.archive_root) else _structured_root(source)
        scan = self._scan_root(source, root) if _series_name(source.name or f.name) else None
        f.archive_root = str(scan or root)
        f.profile = PROFILE_UNIFIED
        f.name_template = ""
        f.folder_layout = "BAT_DAILY" if scan is not None or self._daily_root(root) else UNIFIED_LAYOUT

    def _normalize_definitions(self) -> None:
        for f in self.files:
            self._normalize_file(f)

    @staticmethod
    def _archive_root_for_new(source: Path) -> Path:
        scan = UnifiedPeriodicalsEngine._scan_root(source, source.parent) if _series_name(source.name) else None
        return scan or _structured_root(source)

    @staticmethod
    def _destination(f: PackageFile, value: date) -> Path:
        folder = destination_folder(f.archive_root, value)
        return folder / value.strftime("%d-%m-%Y") if f.folder_layout == "BAT_DAILY" else folder

    def file_identity(self, f: PackageFile) -> str:
        root = clean(f.archive_root) or clean(f.source_path)
        source = Path(f.source_path or f.name)
        series = _series_name(source.name or f.name)
        if series and self._scan_root(source, Path(root)) is not None:
            return root.casefold() + "|" + series.casefold()
        return root.casefold()

    def add_known_file_to_package(self, package_id: str, source_path: str) -> PackageFile:
        row = super().add_known_file_to_package(package_id, source_path)
        self._normalize_file(row)
        return row

    def add_new_file_to_package(self, package_id: str, source_path: str, initial_date: date | None = None) -> PackageFile:
        if package_id not in self.packages or not self.packages[package_id].active:
            raise ValueError("Δεν υπάρχει ενεργό πακέτο.")
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        for f in self.package_files(package_id, active_only=False):
            if clean(f.source_path).casefold() == str(source).casefold():
                f.active = True
                return f

        root = self._archive_root_for_new(source)
        try:
            source_date, _ = filename_date(source.name)
            target_name = source.name
        except ValueError:
            source_date = initial_date or date.today()
            target_name = _dated_name(source.name, source_date)
        definition = PackageFile(package_id, source.name, str(source), archive_root=str(root))
        self._normalize_file(definition)
        target_dir = self._destination(definition, source_date)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / target_name
        if source.resolve() != target.resolve():
            if target.exists():
                raise FileExistsError(str(target))
            target = Path(shutil.move(str(source), str(target)))

        f = PackageFile(
            package_id=package_id, name=target.name, source_path=str(target), active=True,
            profile=PROFILE_UNIFIED, name_template="", prepared_path=str(target),
            prepared_date=source_date.isoformat(), archive_root=str(root), status="ΕΤΟΙΜΟ",
            folder_layout=definition.folder_layout, managed_copy_path="",
        )
        self.files.append(f)
        return f

    def _candidate_files(self, f: PackageFile, allowed_date: date) -> list[tuple[date, Path]]:
        """Find latest from saved checkpoint, then probe only this month's dates.

        Avoid listing year/month/day trees over SMB. The last confirmed path is
        persisted by PeriodicalsService.save, so next run starts there.
        """
        candidates: list[tuple[date, Path]] = []
        seen: set[str] = set()
        source = Path(f.source_path or f.name)
        series = _series_name(source.name or f.name)
        root = Path(f.archive_root) if clean(f.archive_root) else None
        restrict_series = bool(series and root and self._scan_root(source, root) is not None)

        def add(path: Path) -> None:
            if path.name.startswith("~$"):
                return
            if restrict_series and _series_name(path.name) != series:
                return
            key = str(path).casefold()
            if key in seen:
                return
            seen.add(key)
            try:
                d, _ = filename_date(path.name)
            except ValueError:
                return
            if d <= allowed_date and path.is_file():
                candidates.append((d, path))

        # Existing persisted checkpoint always has priority over the initial
        # registration path. The checkpoint is updated and saved by Step 1.
        for raw in (f.prepared_path, f.source_path):
            if clean(raw):
                add(Path(raw))

        if root is None:
            return candidates

        anchor = max(candidates, key=lambda item: item[0]) if candidates else None
        basename = anchor[1].name if anchor is not None else source.name
        # Only the current month, newest day first. At a month boundary the
        # persisted previous-month checkpoint remains available.
        month_start = date(allowed_date.year, allowed_date.month, 1)
        first_day = month_start
        if anchor is not None and anchor[0] >= month_start:
            first_day = anchor[0]
        day = allowed_date
        while day >= first_day:
            target = self._destination(f, day) / _dated_name(basename, day)
            add(target)
            if candidates and candidates[-1][0] == day:
                break
            day -= timedelta(days=1)
        if not candidates:
            # Recovery for a manually renamed source: inspect only the
            # relevant month/day, never earlier years or whole tree.
            month_dir = destination_folder(root, allowed_date)
            try:
                if f.folder_layout == "BAT_DAILY":
                    # Current day and preceding day are sufficient for an
                    # operator's initial re-selection after a rename.
                    for offset in (0, 1):
                        d = allowed_date - timedelta(days=offset)
                        folder = self._destination(f, d)
                        for path in folder.iterdir():
                            add(path)
                else:
                    for path in month_dir.iterdir():
                        add(path)
            except (FileNotFoundError, NotADirectoryError):
                pass
        return candidates

    def latest_existing_prepared(self, f: PackageFile, allowed_date: date):
        candidates = self._candidate_files(f, allowed_date)
        if candidates:
            candidates.sort(key=lambda item: (item[0], str(item[1])))
            return candidates[-1]
        for raw in (f.prepared_path, f.source_path):
            if clean(raw):
                path = Path(raw)
                if path.is_file():
                    return None, path
        return None, None

    def package_next_prepared_date(self, package_id: str, allowed_date: date) -> date:
        min_date = None
        found = False
        for f in self.package_files(package_id):
            d, latest = self.latest_existing_prepared(f, allowed_date)
            if latest is None:
                continue
            found = True
            if d is not None:
                f.prepared_path = str(latest)
                f.prepared_date = d.isoformat()
                f.status = "ΕΤΟΙΜΟ"
                min_date = d if min_date is None or d < min_date else min_date
        return allowed_date if not found or min_date is None else min_date + timedelta(days=1)

    def expected_prepared_path(self, f: PackageFile, d: date):
        if not clean(f.archive_root):
            return None
        _latest_date, latest = self.latest_existing_prepared(f, d)
        base = latest.name if latest is not None else (Path(f.source_path).name or f.name)
        return self._destination(f, d) / _dated_name(base, d)

    def prepare_file(self, f: PackageFile, target_date: date):
        latest_date, source = self.latest_existing_prepared(f, target_date)
        if source is None:
            return None, False
        if latest_date is None:
            target = self._destination(f, target_date) / _dated_name(source.name, target_date)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                if target.exists():
                    return target, False
                target = Path(shutil.move(str(source), str(target)))
            f.source_path = str(target)
            f.name = target.name
            f.prepared_path = str(target)
            f.prepared_date = target_date.isoformat()
            f.status = "ΕΤΟΙΜΟ"
            return target, True
        if latest_date >= target_date:
            canonical = self._destination(f, target_date) / source.name
            if f.folder_layout == "BAT_DAILY" and source.parent != canonical.parent:
                canonical.parent.mkdir(parents=True, exist_ok=True)
                created = not canonical.exists()
                if created:
                    shutil.copy2(source, canonical)
                f.prepared_path = str(canonical)
                f.prepared_date = target_date.isoformat()
                f.status = "ΕΤΟΙΜΟ"
                return canonical, created
            f.prepared_path = str(source)
            f.prepared_date = latest_date.isoformat()
            f.status = "ΕΤΟΙΜΟ"
            return source, False
        target = self._destination(f, target_date) / replace_filename_date(source.name, target_date)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            created = False
        else:
            shutil.copy2(source, target)
            self.__dict__.pop("_periodical_folder_cache", None)
            created = True
        f.prepared_path = str(target)
        f.prepared_date = target_date.isoformat()
        f.status = "ΕΤΟΙΜΟ"
        return target, created

    def prepare_next_package(self, package_id: str, allowed_date: date) -> PreparationResult:
        target = self.package_next_prepared_date(package_id, allowed_date)
        if target > allowed_date:
            needs_daily_layout = any(
                f.folder_layout == "BAT_DAILY" and latest is not None
                and latest.parent != self._destination(f, allowed_date)
                for f in self.package_files(package_id)
                for _day, latest in [self.latest_existing_prepared(f, allowed_date)]
            )
            if not needs_daily_layout:
                return PreparationResult(package_id, target, [], [], [], already_current=True)
            target = allowed_date
        prepared, skipped, failed = [], [], []
        seen: set[str] = set()
        for f in self.package_files(package_id):
            key = self.file_identity(f)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            p, created = self.prepare_file(f, target)
            if p is None:
                failed.append(f.name or Path(f.source_path).name)
            elif created:
                prepared.append(p)
            else:
                skipped.append(p)
        return PreparationResult(package_id, target, prepared, skipped, failed, already_current=False)

    def latest_prepared_path(self, f: PackageFile, allowed_date: date | None = None):
        d, p = self.latest_existing_prepared(f, allowed_date or date.max)
        if p is not None:
            if d is not None:
                f.prepared_date = d.isoformat()
            f.prepared_path = str(p)
            f.status = "ΕΤΟΙΜΟ"
        return p
