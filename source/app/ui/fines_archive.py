from __future__ import annotations

import os
from app.services.pdf_preview import open_document_preview

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout
)

from app.services.fines import FineService


class FinesArchiveDialog(QDialog):
    def __init__(self, service: FineService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("ΑΡΧΕΙΟ ΠΡΟΣΤΙΜΩΝ")
        self.resize(1120, 680)
        root = QVBoxLayout(self)

        title = QLabel("ΑΡΧΕΙΟ ΠΡΟΣΤΙΜΩΝ — ΑΝΑΖΗΤΗΣΗ")
        title.setObjectName("Title")
        root.addWidget(title)

        controls = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Επώνυμο, όνομα, διαβατήριο ή πρωτόκολλο")
        self.query.returnPressed.connect(self.refresh)
        self.kind = QComboBox()
        self.kind.addItem("ΟΛΑ", "")
        self.kind.addItem("ΕΠΙΒΟΛΕΣ", "IMPOSITION")
        self.kind.addItem("ΕΙΣΠΡΑΞΕΙΣ", "PAYMENT")
        self.kind.currentIndexChanged.connect(self.refresh)
        search = QPushButton("ΑΝΑΖΗΤΗΣΗ")
        search.setObjectName("Primary")
        search.clicked.connect(self.refresh)
        controls.addWidget(self.query, 1)
        controls.addWidget(self.kind)
        controls.addWidget(search)
        root.addLayout(controls)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Ημερομηνία/ώρα", "Τύπος", "Επώνυμο", "Όνομα", "Διαβατήριο", "Ποσό",
            "Πρωτόκολλο", "Αστυνομικός / Αρμόδιος", "Αξ. Υπηρεσίας"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        edit = QPushButton("ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ")
        edit.clicked.connect(self.edit_selected)
        delete = QPushButton("ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ")
        delete.clicked.connect(self.delete_selected)
        preview = QPushButton("ΑΝΟΙΓΜΑ ΑΝΑΦΟΡΑΣ ΤΗΣ ΒΑΡΔΙΑΣ")
        preview.clicked.connect(self.preview_selected_shift)
        close = QPushButton("ΚΛΕΙΣΙΜΟ")
        close.clicked.connect(self.accept)
        for widget in (edit, delete, preview, close):
            bottom.addWidget(widget)
        root.addLayout(bottom)
        self.refresh()

    def refresh(self):
        rows = self.service.search_fines(self.query.text(), self.kind.currentData())
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            protocol = row["imposition_protocol"] if row["operation_type"] == "IMPOSITION" else row["collection_protocol"]
            values = [
                (row["occurred_at"] or "").replace("T", " "),
                "ΕΠΙΒΟΛΗ" if row["operation_type"] == "IMPOSITION" else "ΕΙΣΠΡΑΞΗ",
                row["surname"] or "", row["given_name"] or "", row["passport_no"] or "",
                str(row["amount"]), protocol or "", row["responsible"] or "", row["officer_name"] or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, (int(row["id"]), int(row["shift_id"])))
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _selected_ids(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Αρχείο Προστίμων", "Επίλεξε πρώτα μία καταχώριση.")
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def edit_selected(self):
        selected = self._selected_ids()
        if not selected:
            return
        fine_id, _ = selected
        parent = self.parent()
        if parent is None or not hasattr(parent, "begin_edit"):
            QMessageBox.warning(self, "Διόρθωση Προστίμου", "Δεν είναι διαθέσιμη η φόρμα διόρθωσης.")
            return
        try:
            parent.begin_edit(int(fine_id))
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Διόρθωση Προστίμου", str(exc))

    def delete_selected(self):
        selected = self._selected_ids()
        if not selected:
            return
        fine_id, _ = selected
        try:
            row = self.service.get_fine(int(fine_id))
            if row is None:
                raise ValueError("Δεν βρέθηκε η επιλεγμένη πράξη.")
            entry = self.service._row_to_entry(row, for_report=False)
            label = "επιβολή" if row["operation_type"] == "IMPOSITION" else "είσπραξη"
            person = f"{row['surname']} {row['given_name']}".strip()
            message = (
                f"Να διαγραφεί οριστικά η επιλεγμένη {label};\n\n{person} — {row['amount']} €\n\n"
                "Θα ενημερωθούν η συνδεδεμένη είσπραξη, η αναφορά Προστίμων και η Ημερήσια Δραστηριότητα της βάρδιας."
            )
            if QMessageBox.question(self, "Επιβεβαίωση διαγραφής", message, QMessageBox.Yes|QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            result = self.service.delete_fine(int(fine_id), expected_entry=entry)
            self.refresh()
            parent = self.parent()
            if parent is not None and hasattr(parent, "refresh"):
                parent.refresh()
            mw = parent.window() if parent is not None else self.window()
            if hasattr(mw, "pages"):
                for name in ("receipts", "daily", "reports"):
                    page = mw.pages.get(name)
                    if page is not None and hasattr(page, "refresh"):
                        page.refresh()
            if hasattr(mw, "refresh_pending"):
                mw.refresh_pending()
            if result.failed:
                from app.services.pending import PendingService
                details = "\n".join(f"• {PendingService.label(t)}: {error}" for t,error in result.failed)
                QMessageBox.warning(self, "Η πράξη διαγράφηκε", "Η πράξη διαγράφηκε από τα δεδομένα. Οι παρακάτω ενημερώσεις αρχείων έμειναν σε εκκρεμότητα:\n\n" + details)
            else:
                QMessageBox.information(self, "Ολοκληρώθηκε", "Η πράξη διαγράφηκε και όλα τα συνδεδεμένα αρχεία ενημερώθηκαν.")
        except Exception as exc:
            QMessageBox.warning(self, "Διαγραφή Προστίμου", str(exc))

    def preview_selected_shift(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Αρχείο Προστίμων", "Επίλεξε πρώτα μία καταχώριση.")
            return
        _, shift_id = self.table.item(row, 0).data(Qt.UserRole)
        try:
            path = self.service.generate_shift_report(int(shift_id), archive=True)
            if not path:
                raise ValueError("Δεν βρέθηκαν καταχωρίσεις στη συγκεκριμένη βάρδια.")
            if os.name == "nt":
                open_document_preview(path)
            else:
                QMessageBox.information(self, "Προεπισκόπηση", str(path))
        except Exception as exc:
            QMessageBox.warning(self, "Αρχείο Προστίμων", str(exc))
