from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.services.receipts import ReceiptService
from app.ui.widgets import Card


class ReceiptsPage(QWidget):
    def __init__(self, service: ReceiptService, parent=None):
        super().__init__(parent)
        self.service = service
        self.rows = []
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        head = Card()
        title = QLabel('ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ — ΛΙΣΤΕΣ ΠΑΡΑΔΟΣΗΣ')
        title.setObjectName('Title')
        head.layout_box.addWidget(title)
        info = QLabel(
            'Κάθε εισπράττων έχει μία ενεργή λίστα, ανεξάρτητη από την έναρξη/λήξη βάρδιας. '
            'Η λίστα κλείνει μόνο όταν γίνει παράδοση. Μπορείς να προβάλλεις ή να εκτυπώσεις '
            'οποιαδήποτε ενεργή ή κλειστή λίστα χωρίς να αλλάξει η κατάστασή της.'
        )
        info.setWordWrap(True)
        head.layout_box.addWidget(info)
        root.addWidget(head)

        tools = Card()
        row = QHBoxLayout()
        row.addWidget(QLabel('ΦΙΛΤΡΟ ΕΙΣΠΡΑΤΤΟΝΤΑ'))
        self.collector = QComboBox()
        self.collector.setEditable(True)
        self.collector.setMinimumWidth(320)
        self.collector.activated.connect(self.refresh)
        self.collector.lineEdit().returnPressed.connect(self.refresh)
        row.addWidget(self.collector, 1)
        refresh = QPushButton('ΕΜΦΑΝΙΣΗ ΛΙΣΤΩΝ')
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        tools.layout_box.addLayout(row)
        self.state = QLabel()
        self.state.setObjectName('SubTitle')
        tools.layout_box.addWidget(self.state)
        root.addWidget(tools)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            'ΚΑΤΑΣΤΑΣΗ', 'ΕΙΣΠΡΑΤΤΩΝ', 'ΑΝΟΙΓΜΑ', 'ΚΛΕΙΣΙΜΟ',
            'ΕΓΓΡΑΦΕΣ', 'ΣΥΝΟΛΟ', 'ΠΑΡΑΛΑΒΩΝ', 'ΗΜ/ΝΙΑ ΑΡΧΕΙΟΥ',
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        self.table.doubleClicked.connect(self.preview_selected)
        root.addWidget(self.table, 1)

        acts = QHBoxLayout()
        acts.addStretch(1)
        self.preview_btn = QPushButton('ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ ΛΙΣΤΑΣ')
        self.preview_btn.clicked.connect(self.preview_selected)
        acts.addWidget(self.preview_btn)
        self.close_btn = QPushButton('ΚΛΕΙΣΙΜΟ - ΠΑΡΑΔΟΣΗ ΕΝΕΡΓΗΣ ΛΙΣΤΑΣ')
        self.close_btn.setObjectName('Danger')
        self.close_btn.clicked.connect(self.close_selected)
        acts.addWidget(self.close_btn)
        root.addLayout(acts)
        self._sync_actions()

    def _reload_collectors(self):
        current = self.collector.currentText().strip()
        names = self.service.collector_names()
        self.collector.blockSignals(True)
        self.collector.clear()
        self.collector.addItem('')
        self.collector.addItems(names)
        self.collector.setCurrentText(current)
        self.collector.blockSignals(False)

    def _selected_row(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self.rows):
            return None
        return self.rows[r]

    def _sync_actions(self):
        row = self._selected_row()
        self.preview_btn.setEnabled(row is not None and int(row['receipt_count'] or 0) > 0)
        self.close_btn.setEnabled(row is not None and row['status'] == 'OPEN' and int(row['receipt_count'] or 0) > 0)

    def refresh(self):
        self._reload_collectors()
        name = self.collector.currentText().strip()
        self.rows = list(self.service.list_summaries(name))
        self.table.setRowCount(len(self.rows))
        open_count = 0
        for r, x in enumerate(self.rows):
            if x['status'] == 'OPEN':
                open_count += 1
            vals = [
                'ΕΝΕΡΓΗ' if x['status'] == 'OPEN' else 'ΚΛΕΙΣΤΗ',
                x['collector_name'] or '',
                str(x['opened_at'] or '').replace('T', ' '),
                str(x['closed_at'] or '').replace('T', ' '),
                str(x['receipt_count']),
                f"{float(x['total_amount'] or 0):.2f} €",
                x['receiver_name'] or '',
                x['archive_date'] or '',
            ]
            for c, value in enumerate(vals):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, int(x['id']))
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        if name:
            self.state.setText(f'Λίστες για {name}: {len(self.rows)} · ενεργές: {open_count}')
        else:
            self.state.setText(f'Σύνολο λιστών: {len(self.rows)} · ενεργές: {open_count}')
        self._sync_actions()

    def preview_selected(self, *_):
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, 'Λίστες εισπράξεων', 'Επίλεξε πρώτα μία λίστα.')
            return
        try:
            path = self.service.preview_list(int(row['id']))
            self.service.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, 'Προβολή λίστας', str(exc))

    def close_selected(self):
        row = self._selected_row()
        if row is None or row['status'] != 'OPEN':
            QMessageBox.information(self, 'Λίστες εισπράξεων', 'Επίλεξε μία ενεργή λίστα.')
            return
        receiver, ok = QInputDialog.getText(
            self,
            'Παράδοση - Παραλαβή',
            'ΠΑΡΑΛΑΒΩΝ — Ονοματεπώνυμο:',
        )
        if not ok:
            return
        receiver = receiver.strip()
        if not receiver:
            QMessageBox.warning(self, 'Παράδοση - Παραλαβή', 'Συμπλήρωσε τον Παραλαβόντα.')
            return
        collector = row['collector_name'] or ''
        message = (
            f"Να κλείσει οριστικά η ενεργή λίστα;\n\n"
            f"Παραδίδων: {collector}\n"
            f"Παραλαβών: {receiver}\n"
            f"Εγγραφές: {int(row['receipt_count'] or 0)}\n"
            f"Σύνολο: {float(row['total_amount'] or 0):.2f} €\n\n"
            "Η επόμενη είσπραξη του ίδιου εισπράττοντα θα ανοίξει νέα λίστα."
        )
        if QMessageBox.question(
            self, 'Κλείσιμο - Παράδοση λίστας', message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            path = self.service.close_list(collector, receiver)
            self.refresh()
            QMessageBox.information(self, 'Κλείσιμο λίστας', 'Η λίστα έκλεισε και αρχειοθετήθηκε.')
            self.service.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, 'Κλείσιμο λίστας', str(exc))
