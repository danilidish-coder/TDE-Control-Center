from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from app.services.periodicals import IncompletePackageError, PeriodicalsService
from app.ui.widgets import Card


class PackageManagerDialog(QDialog):
    def __init__(self, service: PeriodicalsService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("ΔΙΑΧΕΙΡΙΣΗ ΠΑΚΕΤΩΝ")
        self.resize(820, 620)
        root = QVBoxLayout(self)
        self.pkg = QComboBox(); self.pkg.currentIndexChanged.connect(self._refresh_files)
        root.addWidget(QLabel("Πακέτο")); root.addWidget(self.pkg)
        row = QHBoxLayout()
        for text, slot in (("ΝΕΟ ΠΑΚΕΤΟ", self._new), ("ΜΕΤΟΝΟΜΑΣΙΑ", self._rename), ("ΔΙΑΓΡΑΦΗ ΠΑΚΕΤΟΥ", self._delete)):
            b = QPushButton(text); b.clicked.connect(slot); row.addWidget(b)
        root.addLayout(row)
        self.files = QListWidget(); root.addWidget(self.files, 1)
        row2 = QHBoxLayout()
        add = QPushButton("ΠΡΟΣΘΗΚΗ ΠΕΡΙΟΔΙΚΟΥ"); add.clicked.connect(self._add_file)
        rem = QPushButton("ΑΦΑΙΡΕΣΗ ΠΕΡΙΟΔΙΚΟΥ"); rem.clicked.connect(self._remove_file)
        row2.addWidget(add); row2.addWidget(rem); row2.addStretch(1); root.addLayout(row2)
        self._reload()

    def _id(self): return str(self.pkg.currentData() or "")

    def _reload(self, select_id: str = ""):
        old = select_id or self._id()
        self.engine, _, _ = self.service.load()
        self.pkg.blockSignals(True); self.pkg.clear()
        for p in self.engine.active_packages(): self.pkg.addItem(p.name, p.id)
        if old:
            i = self.pkg.findData(old)
            if i >= 0: self.pkg.setCurrentIndex(i)
        self.pkg.blockSignals(False); self._refresh_files()

    def _refresh_files(self):
        self.files.clear(); pid = self._id()
        if not pid: return
        for f in self.engine.package_files(pid):
            item = QListWidgetItem(f.name or Path(f.source_path).name)
            item.setData(Qt.UserRole, f.source_path); item.setToolTip(f.source_path); self.files.addItem(item)

    def _new(self):
        name, ok = QInputDialog.getText(self, "Νέο πακέτο", "Όνομα νέου πακέτου:")
        if not ok or not name.strip(): return
        try:
            common_root = next((p.root for p in self.engine.active_packages() if p.root), "")
            if not common_root:
                common_root = QFileDialog.getExistingDirectory(self, "Βασικός φάκελος πακέτων")
                if not common_root: return
            pkg = self.service.create_package(name.strip(), common_root); self._reload(pkg.id)
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))

    def _rename(self):
        pid = self._id()
        if not pid: return
        current = self.engine.packages[pid].name
        name, ok = QInputDialog.getText(self, "Μετονομασία πακέτου", "Νέο όνομα:", text=current)
        if not ok or not name.strip(): return
        try: self.service.rename_package(pid, name.strip()); self._reload(pid)
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))

    def _delete(self):
        pid = self._id()
        if not pid: return
        name = self.engine.packages[pid].name
        if QMessageBox.question(self, "Διαγραφή πακέτου", f"Να καταργηθεί το πακέτο «{name}»;\n\nΔεν θα διαγραφεί κανένα αρχικό Περιοδικό ή παλιός φάκελος.") != QMessageBox.Yes:
            return
        try: self.service.delete_package(pid); self._reload()
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))

    def _add_file(self):
        pid = self._id()
        if not pid: return
        try:
            catalog = self.service.catalog(pid)
            choices = [f"{f.name}   —   {f.source_path}" for f in catalog] + ["+ Νέο περιοδικό από αρχείο..."]
            choice, ok = QInputDialog.getItem(self, "Προσθήκη Περιοδικού", "Επιλέξτε Περιοδικό:", choices, 0, False)
            if not ok: return
            idx = choices.index(choice)
            if idx < len(catalog):
                self.service.add_known(pid, catalog[idx].source_path)
            else:
                src, _ = QFileDialog.getOpenFileName(self, "Επιλέξτε το τρέχον αρχείο του Περιοδικού")
                if not src: return
                self.service.add_new(pid, src)
            self._reload(pid)
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))

    def _remove_file(self):
        pid = self._id(); item = self.files.currentItem()
        if not pid or item is None: return
        src = str(item.data(Qt.UserRole) or "")
        if QMessageBox.question(self, "Αφαίρεση Περιοδικού", f"Να αφαιρεθεί το «{item.text()}» μόνο από αυτό το πακέτο;\n\nΤο αρχικό αρχείο δεν θα διαγραφεί.") != QMessageBox.Yes:
            return
        try: self.service.remove(pid, src); self._reload(pid)
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))


class PeriodicalsPage(QWidget):
    def __init__(self, service: PeriodicalsService, parent=None):
        super().__init__(parent); self.service = service; self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(12)
        card = Card(); title = QLabel("ΠΕΡΙΟΔΙΚΑ"); title.setObjectName("Title"); card.layout_box.addWidget(title)
        text = QLabel("Όλα τα Περιοδικά ακολουθούν την ίδια λογική: αντιγραφή του τελευταίου πραγματικού αρχείου, αλλαγή μόνο της ημερομηνίας και αρχειοθέτηση ανά Έτος / Μήνα.")
        text.setWordWrap(True); card.layout_box.addWidget(text)
        card.layout_box.addWidget(QLabel("Πακέτο")); self.pkg = QComboBox(); self.pkg.currentIndexChanged.connect(self._refresh_info); card.layout_box.addWidget(self.pkg)
        self.info = QLabel(); self.info.setWordWrap(True); card.layout_box.addWidget(self.info)
        row = QHBoxLayout()
        prep = QPushButton("ΕΝΗΜΕΡΩΣΗ ΑΡΧΕΙΩΝ"); prep.setObjectName("Primary"); prep.clicked.connect(self.prepare)
        ready = QPushButton("ΕΤΟΙΜΟ ΠΑΚΕΤΟ"); ready.clicked.connect(self.sync)
        latest = QPushButton("ΑΝΟΙΓΜΑ ΠΙΟ ΠΡΟΣΦΑΤΩΝ"); latest.clicked.connect(self.open_latest)
        row.addWidget(prep); row.addWidget(ready); row.addWidget(latest); card.layout_box.addLayout(row)
        manage = QPushButton("ΔΙΑΧΕΙΡΙΣΗ ΠΑΚΕΤΩΝ"); manage.clicked.connect(self.manage); card.layout_box.addWidget(manage)
        root.addWidget(card); root.addStretch(1)

    def _id(self): return str(self.pkg.currentData() or "")

    def refresh(self):
        current = self._id() if hasattr(self, "pkg") else ""
        self.engine, _, _ = self.service.load()
        self.pkg.blockSignals(True); self.pkg.clear()
        for p in self.engine.active_packages(): self.pkg.addItem(p.name, p.id)
        if current:
            i = self.pkg.findData(current)
            if i >= 0: self.pkg.setCurrentIndex(i)
        self.pkg.blockSignals(False); self._refresh_info()

    def _refresh_info(self):
        pid = self._id()
        if not pid or pid not in self.engine.packages:
            self.info.setText("Δεν υπάρχει ενεργό πακέτο."); return
        p = self.engine.packages[pid]; files = self.engine.package_files(pid)
        self.info.setText(f"{p.name} · {len(files)} ενεργά αρχεία\nΠρος: {p.to or '—'}\n{p.notes or ''}")

    def manage(self):
        current = self._id(); PackageManagerDialog(self.service, self).exec(); self.refresh()
        if current:
            i = self.pkg.findData(current)
            if i >= 0: self.pkg.setCurrentIndex(i)

    def prepare(self):
        try:
            r = self.service.prepare_package(self._id())
            msg = f"Ημερομηνία: {r.target_date:%d/%m/%Y}\nΔημιουργήθηκαν: {len(r.prepared)}\nΥπήρχαν ήδη: {len(r.skipped_existing)}"
            if r.failed: msg += f"\nΧρειάζονται έλεγχο: {len(r.failed)}"
            QMessageBox.information(self, "Περιοδικά", msg); self.refresh()
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))

    def sync(self):
        while True:
            try:
                folder = self.service.sync_package(self._id())
                QMessageBox.information(self, "Έτοιμο πακέτο", str(folder)); self.service.open_path(folder); self.refresh(); return
            except IncompletePackageError as exc:
                details = []
                if exc.missing: details.append("Δεν βρέθηκαν:\n• " + "\n• ".join(exc.missing))
                if exc.failed: details.append("Δεν αντιγράφηκαν μετά από 3 προσπάθειες:\n• " + "\n• ".join(exc.failed))
                choice = QMessageBox.warning(
                    self, "Ελλιπές πακέτο - " + exc.package_name,
                    "Το πακέτο δεν ενημερώθηκε πλήρως.\n\n" + "\n\n".join(details) +
                    "\n\nΕΠΑΝΑΛΗΨΗ = ξαναδοκιμάζει όλο το πακέτο.\nΠΑΡΑΒΛΕΨΗ = συνεχίζει με τα υπόλοιπα αρχεία.\nΜΑΤΑΙΩΣΗ = σταματά.",
                    QMessageBox.Retry | QMessageBox.Ignore | QMessageBox.Abort, QMessageBox.Retry)
                if choice == QMessageBox.Retry: continue
                if choice == QMessageBox.Ignore:
                    QMessageBox.warning(self, "Συνέχεια με ελλιπές πακέτο", f"Ενημερώθηκαν: {exc.copied} από {exc.active} ενεργά αρχεία.\n\nΕλέγξτε τον μόνιμο φάκελο πριν την αποστολή.")
                    self.service.open_path(exc.folder)
                return
            except Exception as exc:
                QMessageBox.warning(self, "Περιοδικά", str(exc)); return

    def open_latest(self):
        try:
            paths = self.service.latest_paths(self._id())
            if not paths: raise FileNotFoundError("Δεν υπάρχει ακόμη πρόσφατο αρχείο. Πατήστε πρώτα ΕΝΗΜΕΡΩΣΗ ΑΡΧΕΙΩΝ.")
            for p in paths: self.service.open_path(p)
        except Exception as exc: QMessageBox.warning(self, "Περιοδικά", str(exc))
