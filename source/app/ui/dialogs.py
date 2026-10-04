from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout


class StartShiftDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Έναρξη Βάρδιας")
        self.setMinimumWidth(430)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.rank = QLineEdit()
        self.rank.setPlaceholderText("ΒΑΘΜΟΣ")
        self.agms = QLineEdit()
        self.agms.setPlaceholderText("Α.Γ.Μ.Σ.")
        self.surname = QLineEdit()
        self.surname.setPlaceholderText("Επώνυμο")
        self.name = QLineEdit()
        self.name.setPlaceholderText("Όνομα")
        form.addRow("ΒΑΘΜΟΣ", self.rank)
        form.addRow("Α.Γ.Μ.Σ.", self.agms)
        form.addRow("ΕΠΩΝΥΜΟ", self.surname)
        form.addRow("ΟΝΟΜΑ", self.name)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ΕΝΑΡΞΗ")
        buttons.button(QDialogButtonBox.Cancel).setText("ΑΚΥΡΩΣΗ")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        if not self.rank.text().strip():
            QMessageBox.warning(self, "Έλεγχος", "Συμπλήρωσε τον Βαθμό.")
            return
        if not self.agms.text().strip():
            QMessageBox.warning(self, "Έλεγχος", "Συμπλήρωσε το ΑΓΜΣ.")
            return
        if not self.surname.text().strip():
            QMessageBox.warning(self, "Έλεγχος", "Συμπλήρωσε το Επώνυμο.")
            return
        if not self.name.text().strip():
            QMessageBox.warning(self, "Έλεγχος", "Συμπλήρωσε το Όνομα.")
            return
        self.accept()
