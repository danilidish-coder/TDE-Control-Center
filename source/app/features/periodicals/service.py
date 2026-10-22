from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from app.core.lock import SharedWriteLock
from app.core.paths import resource_path, runtime_root
from app.shared.documents.common import clean, operational_date
from app.features.periodicals.engine import (
    IncompletePackageError, Package, PackageFile,
    PreparationResult, PROFILE_AS_IS, PROFILE_DAILY_FOLDER, PROFILE_SAME_FOLDER,
)
from app.features.periodicals.unified_engine import UnifiedPeriodicalsEngine, PROFILE_UNIFIED


class PeriodicalsService:
    """Persistence/UI service for the unified periodicals engine.

    Old profile metadata is accepted for migration, but all active periodicals
    are handled by one Year -> Month / copy-latest rule.
    """

    def __init__(self):
        self.root = runtime_root() / "periodicals"
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile = self.root / "periodicals_profile.json"
        self.lock = SharedWriteLock(self.root)
        if not self.profile.exists():
            shutil.copy2(resource_path("periodicals_profile.json"), self.profile)

    def load(self) -> tuple[UnifiedPeriodicalsEngine, dict, Path]:
        with self.lock.acquire():
            data = json.loads(self.profile.read_text(encoding="utf-8"))
        packages = [Package(**x) for x in data.get("packages", [])]
        files = [PackageFile(**x) for x in data.get("files", [])]
        return UnifiedPeriodicalsEngine(packages, files), data, self.profile

    def save(self, engine: UnifiedPeriodicalsEngine, data: dict, path: Path | None = None) -> None:
        path = path or self.profile
        payload = dict(data)
        payload["packages"] = [asdict(p) for p in sorted(engine.packages.values(), key=lambda x: x.order)]
        payload["files"] = [asdict(f) for f in engine.files]
        with self.lock.acquire():
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)

    def _mutate(self, fn):
        engine, data, path = self.load()
        result = fn(engine)
        self.save(engine, data, path)
        return result

    def create_package(self, name: str, root: str = "") -> Package:
        return self._mutate(lambda e: e.create_package(name, root=root))

    def rename_package(self, package_id: str, new_name: str) -> Package:
        return self._mutate(lambda e: e.rename_package(package_id, new_name))

    def delete_package(self, package_id: str) -> None:
        self._mutate(lambda e: e.delete_package(package_id))

    def catalog(self, package_id: str = "") -> list[PackageFile]:
        engine, _, _ = self.load()
        active = {clean(f.source_path).casefold() for f in engine.package_files(package_id)} if package_id else set()
        return [f for f in engine.catalog_files() if clean(f.source_path).casefold() not in active]

    def add_known(self, package_id: str, source_path: str) -> PackageFile:
        return self._mutate(lambda e: e.add_known_file_to_package(package_id, source_path))

    def add_new(self, package_id: str, source_path: str, when: datetime | None = None) -> PackageFile:
        when = when or datetime.now()
        initial = operational_date(when)
        return self._mutate(lambda e: e.add_new_file_to_package(package_id, source_path, initial))

    def remove(self, package_id: str, source_path: str) -> None:
        self._mutate(lambda e: e.remove_file_from_package(package_id, source_path))

    def prepare_package(self, package_id: str, when: datetime | None = None) -> PreparationResult:
        when = when or datetime.now()
        allowed = operational_date(when)
        engine, data, path = self.load()
        result = engine.prepare_next_package(package_id, allowed)
        self.save(engine, data, path)
        return result

    def prepare_all_for_date(self, target_date: date) -> dict[str, list[str]]:
        engine, data, path = self.load()
        result: dict[str, list[str]] = {}
        processed: dict[str, Path] = {}
        for pkg in engine.active_packages():
            paths: list[str] = []
            for f in engine.package_files(pkg.id):
                key = engine.file_identity(f)
                if key and key in processed:
                    out = processed[key]
                    f.prepared_path = str(out)
                    f.prepared_date = target_date.isoformat()
                    f.status = "ΕΤΟΙΜΟ"
                    paths.append(str(out))
                    continue
                out, _created = engine.prepare_file(f, target_date)
                if out is not None:
                    processed[key] = out
                    paths.append(str(out))
            result[pkg.id] = paths
        self.save(engine, data, path)
        return result

    def sync_package(self, package_id: str, when: datetime | None = None) -> Path:
        when = when or datetime.now()
        allowed = operational_date(when)
        engine, data, path = self.load()
        try:
            folder = engine.sync_package_folder(package_id, allowed)
        except (IncompletePackageError, FileNotFoundError, ValueError):
            self.save(engine, data, path)
            raise
        self.save(engine, data, path)
        return folder

    def latest_paths(self, package_id: str, when: datetime | None = None) -> list[Path]:
        when = when or datetime.now()
        allowed = operational_date(when)
        engine, data, path = self.load()
        out: list[Path] = []
        for f in engine.package_files(package_id):
            q = engine.latest_prepared_path(f, allowed)
            if q is not None:
                out.append(q)
        self.save(engine, data, path)
        return out

    @staticmethod
    def open_path(path: str | Path) -> None:
        if os.name == "nt":
            os.startfile(str(path))


__all__ = [
    "PeriodicalsService", "IncompletePackageError", "PROFILE_UNIFIED",
    "PROFILE_AS_IS", "PROFILE_SAME_FOLDER", "PROFILE_DAILY_FOLDER",
]
