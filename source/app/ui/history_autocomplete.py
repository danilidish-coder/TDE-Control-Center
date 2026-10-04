from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter, QLineEdit


def install_history_completer(widget: QLineEdit, values: list[str]) -> None:
    """Attach Excel-like suggestions from values already stored in the service database."""
    clean = []
    seen = set()
    for raw in values:
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            clean.append(value)
    model = QStringListModel(clean, widget)
    completer = QCompleter(model, widget)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchStartsWith)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    completer.setMaxVisibleItems(12)
    widget.setCompleter(completer)
    widget._history_completion_model = model
    widget._history_completer = completer
