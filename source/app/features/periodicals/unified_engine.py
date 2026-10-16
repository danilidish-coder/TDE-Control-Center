from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

from app.shared.documents.common import clean
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

    def _normalize_definitions(self) -> None:
        for f in self.files:
            source = Path(f.source_path) if clean(f.source_path) else Path(f.name)
            root = Path(f.archive_root) if clean(f.archive_root) else _structured_root(source)
            series = _series_name(source.name or f.name)
            if series and root.name.casefold() == "1. scan folder reports".casefold():
                root = root / series
            f.archive_root = str(root)
            f.profile = PROFILE_UNIFIED
            f.name_template = ""
            f.folder_layout = UNIFIED_LAYOUT

    @staticmethod
    def _archive_root_for_new(source: Path) -> Path:
        series = _series_name(source.name)
        if series:
            for ancestor in source.parents:
                if ancestor.name.casefold() == "1. scan folder reports".casefold():
                    return ancestor / series
        return _structured_root(source)

    def add_known_file_to_package(self, package_id: str, source_path: str) -> PackageFile:
        row = super().add_known_file_to_package(package_id, source_path)
        source = Path(row.source_path) if clean(row.source_path) else Path(row.name)
        root = Path(row.archive_root) if clean(row.archive_root) else _structured_root(source)
        series = _series_name(source.name or row.name)
        if series and root.name.casefold() == "1. scan folder reports".casefold():
            root = root / series
        row.archive_root = str(root)
        row.profile = PROFILE_UNIFIED
        row.name_template = ""
        row.folder_layout = UNIFIED_LAYOUT
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
        target_dir = destination_folder(root, source_date)
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
            folder_layout=UNIFIED_LAYOUT, managed_copy_path="",
        )
        self.files.append(f)
        return f

    def _candidate_files(self, f: PackageFile, allowed_date: date) -> list[tuple[date, Path]]:
        candidates: list[tuple[date, Path]] = []
        seen: set[str] = set()

        def add(path: Path) -> None:
            if not path.is_file():
                return
            try:
                key = str(path.resolve()).casefold()
            except Exception:
                key = str(path).casefold()
            if key in seen:
                return
            seen.add(key)
            try:
                d, _ = filename_date(path.name)
            except ValueError:
                return
            if d <= allowed_date:
                candidates.append((d, path))

        if clean(f.archive_root):
            root = Path(f.archive_root)
            if root.exists():
                for path in root.rglob("*"):
                    if path.is_file():
                        add(path)
        if clean(f.prepared_path):
            add(Path(f.prepared_path))
        if clean(f.source_path):
            add(Path(f.source_path))
        return candidates

    def latest_existing_prepared(self, f: PackageFile, allowed_date: date):
        candidates = self._candidate_files(f, allowed_date)
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1].stat().st_mtime_ns, str(item[1])))
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
        return destination_folder(f.archive_root, d) / _dated_name(base, d)

    def prepare_file(self, f: PackageFile, target_date: date):
        latest_date, source = self.latest_existing_prepared(f, target_date)
        if source is None:
            return None, False
        if latest_date is None:
            target = destination_folder(f.archive_root or source.parent, target_date) / _dated_name(source.name, target_date)
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
            f.prepared_path = str(source)
            f.prepared_date = latest_date.isoformat()
            f.status = "ΕΤΟΙΜΟ"
            return source, False
        target = destination_folder(f.archive_root, target_date) / replace_filename_date(source.name, target_date)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            created = False
        else:
            shutil.copy2(source, target)
            created = True
        f.prepared_path = str(target)
        f.prepared_date = target_date.isoformat()
        f.status = "ΕΤΟΙΜΟ"
        return target, created

    def prepare_next_package(self, package_id: str, allowed_date: date) -> PreparationResult:
        target = self.package_next_prepared_date(package_id, allowed_date)
        if target > allowed_date:
            return PreparationResult(package_id, target, [], [], [], already_current=True)
        prepared, skipped, failed = [], [], []
        seen: set[str] = set()
        for f in self.package_files(package_id):
            key = (clean(f.archive_root) or clean(f.source_path)).casefold()
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
