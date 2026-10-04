from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "resources"
    return app_root() / "resources"


def resource_path(name: str) -> Path:
    p = resource_root() / name
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def runtime_root() -> Path:
    path = app_root() / ".tde_runtime"
    path.mkdir(parents=True, exist_ok=True)
    _hide_on_windows(path)
    return path


def resolve_runtime_path(value: str | Path) -> Path:
    """Resolve stored paths after the whole .tde_runtime folder has moved.

    Existing absolute paths from older versions are accepted. If the same
    relative file exists under the current .tde_runtime, the current copy wins.
    """
    raw = str(value or "").strip()
    if not raw:
        return Path()

    p = Path(raw)
    parts = p.parts
    lowered = [str(x).lower() for x in parts]

    if ".tde_runtime" in lowered:
        idx = lowered.index(".tde_runtime")
        rel = Path(*parts[idx + 1:])
        candidate = runtime_root() / rel
        if candidate.exists():
            return candidate
        if p.exists():
            return p
        return candidate

    if not p.is_absolute():
        candidate = runtime_root() / p
        if candidate.exists():
            return candidate

    return p


def db_path() -> Path:
    return runtime_root() / "tde_control_center.sqlite3"


def archive_root() -> Path:
    path = runtime_root() / "archive"
    path.mkdir(parents=True, exist_ok=True)
    return path


def preview_root() -> Path:
    path = runtime_root() / "preview"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_root() -> Path:
    path = runtime_root() / "backup"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _hide_on_windows(path: Path) -> None:
    if os.name != "nt":
        return
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass
