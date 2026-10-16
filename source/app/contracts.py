"""Small integration contracts; no Qt, feature implementation or entry imports."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class Navigation(Protocol):
    def show_reports(self, report_type: str = "") -> None: ...
    def refresh_pages(self, names: tuple[str, ...]) -> None: ...
    def refresh_pending(self) -> None: ...


@dataclass(frozen=True)
class PageActions:
    """Callbacks injected by the composition root, optional for standalone pages."""
    show_reports: Callable[[str], None] = lambda report_type: None
    refresh_pages: Callable[[tuple[str, ...]], None] = lambda names: None
    refresh_pending: Callable[[], None] = lambda: None


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    title: str | None
    icon: str | None
    create_page: Callable[[Any], Any]
