from __future__ import annotations

import os
from app.services.pdf_preview import open_document_preview
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.ui.widgets import Card


REPORT_LABELS = {
    "FINES": "ΠΡΟΣΤΙΜΑ",
    "VAS": "ΒΑΣ",
    "DAILY": "ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ",
}


class ShiftReportsPage(QWidget):
    def __init__(self, db, fines, refusals, daily, parent=None):
        super().__init__(parent)
        self.db = db
        self.fines = fines
        self.refusals = refusals
        self.daily = daily
        self.rows = []
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        head = Card()
        self.title = QLabel("ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ")
        self.title.setObjectName("Title")
        head.layout_box.addWidget(self.title)
        note = QLabel(
            "Όλες οι αναφορές των κλεισμένων βαρδιών. "
            "Διπλό κλικ σε μία γραμμή ανοίγει την αναφορά."
        )
        note.setWordWrap(True)
        head.layout_box.addWidget(note)
        root.addWidget(head)

        filters = Card()
        row = QHBoxLayout()
        self.report_type = QComboBox()
        self.report_type.addItem("ΟΛΕΣ ΟΙ ΑΝΑΦΟΡΕΣ", "")
        self.report_type.addItem("ΠΡΟΣΤΙΜΑ", "FINES")
        self.report_type.addItem("ΒΑΣ", "VAS")
        self.report_type.addItem("ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ", "DAILY")
        self.report_type.currentIndexChanged.connect(self.refresh)
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("ΑΠΟ ΗΗ/ΜΜ/ΕΕΕΕ")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("ΕΩΣ ΗΗ/ΜΜ/ΕΕΕΕ")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Αξιωματικός ή Α.Γ.Μ.Σ. (προαιρετικό)")
        search_btn = QPushButton("ΑΝΑΖΗΤΗΣΗ")
        search_btn.setObjectName("Primary")
        search_btn.clicked.connect(self.refresh)
        row.addWidget(self.report_type, 1)
        row.addWidget(self.date_from, 1)
        row.addWidget(self.date_to, 1)
        row.addWidget(self.search, 2)
        row.addWidget(search_btn)
        filters.layout_box.addLayout(row)
        root.addWidget(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "ΒΑΡΔΙΑ", "ΤΥΠΟΣ ΑΝΑΦΟΡΑΣ", "ΑΞΙΩΜΑΤΙΚΟΣ ΥΠΗΡΕΣΙΑΣ", "Α.Γ.Μ.Σ.", "ΑΡΧΕΙΟ",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.open_selected)
        root.addWidget(self.table, 1)

        self.info = QLabel("")
        self.info.setObjectName("SubTitle")
        root.addWidget(self.info)

        self.search.returnPressed.connect(self.refresh)
        self.date_from.returnPressed.connect(self.refresh)
        self.date_to.returnPressed.connect(self.refresh)

    @staticmethod
    def _parse_date(text: str):
        value = text.strip()
        if not value:
            return None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"Μη έγκυρη ημερομηνία: {value}")

    def set_report_type(self, kind: str = ""):
        kind = kind or ""
        idx = self.report_type.findData(kind)
        self.report_type.setCurrentIndex(max(0, idx))
        locked = bool(kind)
        self.report_type.setVisible(not locked)
        if kind == "FINES":
            self.title.setText("ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ")
        elif kind == "VAS":
            self.title.setText("ΑΡΧΕΙΟ ΒΑΣ")
        elif kind == "DAILY":
            self.title.setText("ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ")
        else:
            self.title.setText("ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ")
        self.refresh()

    def _closed_shifts(self):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT s.*,
                       (SELECT COUNT(*) FROM fines f WHERE f.shift_id=s.id) AS fines_count,
                       (SELECT COUNT(*) FROM refusals r WHERE r.shift_id=s.id) AS refusals_count
                FROM shifts s
                WHERE s.status='CLOSED'
                ORDER BY s.started_at DESC, s.id DESC
                """
            ).fetchall()

    def refresh(self):
        try:
            date_from = self._parse_date(self.date_from.text())
            date_to = self._parse_date(self.date_to.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Αρχείο Αναφορών", str(exc))
            return
        if date_from and date_to and date_from > date_to:
            QMessageBox.warning(self, "Αρχείο Αναφορών", "Η ημερομηνία «Από» είναι μετά την ημερομηνία «Έως».")
            return

        wanted = self.report_type.currentData() or ""
        query = self.search.text().strip().casefold()
        rows = []
        for shift in self._closed_shifts():
            try:
                start = datetime.fromisoformat(shift["started_at"])
                end = datetime.fromisoformat(shift["ended_at"])
            except Exception:
                continue
            if date_from and start.date() < date_from:
                continue
            if date_to and start.date() > date_to:
                continue
            haystack = f"{shift['officer_name']} {shift['officer_agms']} {shift['officer_rank_full']}".casefold()
            if query and query not in haystack:
                continue

            available = [("DAILY", True)]
            if int(shift["fines_count"] or 0):
                available.insert(0, ("FINES", True))
            if int(shift["refusals_count"] or 0):
                pos = 1 if available and available[0][0] == "FINES" else 0
                available.insert(pos, ("VAS", True))
            for kind, _ in available:
                if wanted and kind != wanted:
                    continue
                rows.append((shift, kind, start, end))

        self.rows = rows
        self.table.setRowCount(len(rows))
        for r, (shift, kind, start, end) in enumerate(rows):
            shift_text = f"{start:%d/%m/%Y %H:%M} → {end:%d/%m/%Y %H:%M}"
            officer = " ".join(v for v in (shift["officer_rank_full"], shift["officer_name"]) if v)
            values = [shift_text, REPORT_LABELS[kind], officer, shift["officer_agms"] or "", "ΔΙΠΛΟ ΚΛΙΚ ΓΙΑ ΑΝΟΙΓΜΑ"]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 0:
                    item.setData(Qt.UserRole, (int(shift["id"]), kind))
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.info.setText(f"Αναφορές που βρέθηκαν: {len(rows)}")

    @staticmethod
    def _open(path: str | Path):
        p = Path(path)
        if os.name == "nt":
            open_document_preview(p)
        else:
            return p

    def open_selected(self, *_):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        shift_id, kind = item.data(Qt.UserRole)
        shift_id = int(shift_id)
        kind = str(kind)
        try:
            if kind == "FINES":
                path = self.fines.generate_shift_report(shift_id, archive=True)
                if path is None:
                    raise ValueError("Η βάρδια δεν έχει καταχωρίσεις Προστίμων.")
            elif kind == "VAS":
                path = self.refusals.generate_vas(shift_id, archive=True)
                if path is None:
                    raise ValueError("Η βάρδια δεν έχει Αρνήσεις Εισόδου.")
            elif kind == "DAILY":
                path = self.daily.generate(shift_id, archive=True)
            else:
                raise ValueError("Άγνωστος τύπος αναφοράς.")
            self._open(path)
        except Exception as exc:
            QMessageBox.warning(self, "Αρχείο Αναφορών", str(exc))
