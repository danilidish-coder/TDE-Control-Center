from __future__ import annotations
from app.contracts import PageActions

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget
)

from app.ui.widgets import Card


NUMERIC_GROUPS = [
    ("Λοιπές πράξεις", [
        ("Απαγόρευση εξόδου", "exit_bans"),
        ("Μη επιβολή προστίμου — Άρθρο 16 §1α", "no_fine_art16_1a"),
        ("Εκτέλεση απελάσεων", "deportations"),
        ("Εκτέλεση επαναπροωθήσεων", "readmissions"),
        ("Υπηρεσιακά σημειώματα", "service_notes"),
    ]),
    ("Προσαγωγές", [
        ("Ημεδαποί", "presentations_greek"),
        ("Αλλοδαποί", "presentations_foreign"),
        ("Μετατράπηκαν σε σύλληψη — ημεδαποί", "presentation_to_arrest_greek"),
        ("Μετατράπηκαν σε σύλληψη — αλλοδαποί", "presentation_to_arrest_foreign"),
    ]),
    ("Συλλήψεις Υπηρεσίας", [
        ("Ευρωπαϊκό ένταλμα σύλληψης", "our_arrests_eaw"),
        ("Διεθνές ένταλμα σύλληψης", "our_arrests_int_warrant"),
        ("Διωκτικά / αποφάσεις", "our_arrests_decisions"),
        ("Ανυπότακτος εσωτερικού", "our_arrests_draft_evasion"),
        ("Άλλο", "our_arrests_other"),
    ]),
    ("Συλλήψεις άλλων Υπηρεσιών", [
        ("Ευρωπαϊκό ένταλμα σύλληψης", "other_arrests_eaw"),
        ("Διεθνές ένταλμα σύλληψης", "other_arrests_int_warrant"),
        ("Διωκτικά / αποφάσεις", "other_arrests_decisions"),
        ("Ανυπότακτος εσωτερικού", "other_arrests_draft_evasion"),
        ("Άλλο", "other_arrests_other"),
    ]),
    ("Έλεγχοι", [
        ("Ι.Χ.Ε.", "vehicles_car"),
        ("Ι.Χ.Φ.", "vehicles_private_truck"),
        ("Δ.Χ.Φ.", "vehicles_public_truck"),
        ("Λεωφορεία", "vehicles_bus"),
        ("Συσκευή καρδιακών παλμών", "heart_rate_checks"),
        ("Προσπάθειες λήψης αποτυπωμάτων VIS", "vis_attempts"),
        ("Έλεγχοι AFIS", "afis_checks"),
        ("Βεβαίωση τροχαίων παραβάσεων", "traffic_violations"),
        ("Παράνομο κόμιστρο", "illegal_fare"),
    ]),
    ("Άρνηση H — αλλαγή ονόματος", [
        ("Δ.Κ.Α. με αλλαγή ονόματος", "h_dka_name_change"),
        ("S.I.S. με αλλαγή ονόματος", "h_sis_name_change"),
        ("Δ.Κ.Α. & S.I.S. με αλλαγή ονόματος", "h_both_name_change"),
    ]),
]

TEXT_FIELDS = [
    ("Υπηκοότητα συλληφθέντος — Υπηρεσία μας", "our_arrests_nationality"),
    ("Υπηκοότητα συλληφθέντος — άλλη Υπηρεσία", "other_arrests_nationality"),
    ("Υπηρεσία σύλληψης", "other_arrests_service"),
]


class DailyArchiveDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ")
        self.resize(900, 520)
        lay = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Βάρδια", "Έναρξη", "Λήξη", "Αξιωματικός", "Αρχείο"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        filters = QHBoxLayout()
        self.date_from = QLineEdit(); self.date_from.setPlaceholderText("ΑΠΟ ΗΗ/ΜΜ/ΕΕΕΕ")
        self.date_to = QLineEdit(); self.date_to.setPlaceholderText("ΕΩΣ ΗΗ/ΜΜ/ΕΕΕΕ")
        filter_btn = QPushButton("ΦΙΛΤΡΟ"); filter_btn.clicked.connect(self.refresh)
        clear_btn = QPushButton("ΚΑΘΑΡΙΣΜΟΣ"); clear_btn.clicked.connect(self.clear_filter)
        filters.addWidget(self.date_from); filters.addWidget(self.date_to); filters.addWidget(filter_btn); filters.addWidget(clear_btn)
        lay.addLayout(filters)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        open_btn = QPushButton("ΑΝΟΙΓΜΑ ΕΠΙΛΕΓΜΕΝΗΣ")
        open_btn.clicked.connect(self.open_selected)
        folder_btn = QPushButton("ΑΝΟΙΓΜΑ ΦΑΚΕΛΟΥ ΑΡΧΕΙΟΥ"); folder_btn.clicked.connect(self.open_folder)
        self.stat_month = QSpinBox(); self.stat_month.setRange(1, 12); self.stat_month.setValue(datetime.now().month); self.stat_month.setPrefix("ΜΗΝΑΣ ")
        self.stat_year = QSpinBox(); self.stat_year.setRange(2000, 2100); self.stat_year.setValue(datetime.now().year); self.stat_year.setPrefix("ΕΤΟΣ ")
        monthly = QPushButton("ΜΗΝΙΑΙΟ ΣΤΑΤΙΣΤΙΚΟ"); monthly.clicked.connect(self.monthly_stats)
        yearly = QPushButton("ΕΤΗΣΙΟ ΣΤΑΤΙΣΤΙΚΟ"); yearly.clicked.connect(self.yearly_stats)
        row.addWidget(open_btn); row.addWidget(folder_btn); row.addStretch(1)
        row.addWidget(self.stat_month); row.addWidget(self.stat_year); row.addWidget(monthly); row.addWidget(yearly)
        lay.addLayout(row)
        self.refresh()

    @staticmethod
    def _date(text):
        text = text.strip()
        return datetime.strptime(text, "%d/%m/%Y").date() if text else None

    def clear_filter(self):
        self.date_from.clear()
        self.date_to.clear()
        self.refresh()

    def refresh(self):
        try:
            date_from = self._date(self.date_from.text())
            date_to = self._date(self.date_to.text())
        except ValueError:
            QMessageBox.warning(self, "Φίλτρο", "Οι ημερομηνίες πρέπει να είναι σε μορφή ΗΗ/ΜΜ/ΕΕΕΕ.")
            return
        rows = list(self.service.list_archive())
        if date_from or date_to:
            filtered = []
            for item in rows:
                try:
                    value = datetime.fromisoformat(item["started_at"]).date()
                except Exception:
                    continue
                if date_from and value < date_from:
                    continue
                if date_to and value > date_to:
                    continue
                filtered.append(item)
            rows = filtered
        self.table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            vals = [item["shift_id"], (item["started_at"] or "").replace("T", " "),
                    (item["ended_at"] or "").replace("T", " "), item["officer_name"], item["archive_path"] or ""]
            for c, value in enumerate(vals):
                it = QTableWidgetItem(str(value))
                if c == 0:
                    it.setData(Qt.UserRole, int(item["shift_id"]))
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()

    def open_folder(self):
        try:
            self.service.open_archive_folder()
        except Exception as exc:
            QMessageBox.warning(self, "Φάκελος αρχείου", str(exc))

    def monthly_stats(self):
        try:
            path = self.service.generate_statistics(self.stat_year.value(), self.stat_month.value())
            self.service.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Μηνιαίο στατιστικό", str(exc))

    def yearly_stats(self):
        try:
            path = self.service.generate_statistics(self.stat_year.value())
            self.service.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Ετήσιο στατιστικό", str(exc))

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        path = self.table.item(row, 4).text().strip()
        if not path:
            QMessageBox.information(self, "Αρχείο", "Δεν έχει δημιουργηθεί ακόμη αρχειοθετημένο αρχείο για αυτή τη βάρδια.")
            return
        self.service.open_file(path)


class DailyActivityPage(QWidget):
    actions = PageActions()
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.inputs: dict[str, QWidget] = {}
        self.auto_edit_inputs: dict[str, tuple[QSpinBox, str]] = {}
        self.auto_labels: dict[str, QLabel] = {}
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(12)

        top = Card()
        title = QLabel("ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ"); title.setObjectName("Title")
        desc = QLabel("Αρνήσεις και Πρόστιμα ενημερώνονται αυτόματα από την κοινή βάρδια. Συμπληρώνονται μόνο τα στοιχεία που δεν γνωρίζει η εφαρμογή.")
        desc.setWordWrap(True)
        top.layout_box.addWidget(title); top.layout_box.addWidget(desc)
        self.shift_label = QLabel(); self.shift_label.setWordWrap(True); top.layout_box.addWidget(self.shift_label)
        root.addWidget(top)

        auto = Card(); auto.layout_box.addWidget(QLabel("ΑΥΤΟΜΑΤΑ ΣΤΟΙΧΕΙΑ ΒΑΡΔΙΑΣ"))
        grid = QGridLayout(); auto.layout_box.addLayout(grid)
        auto_items = [
            ("Σύνολο Αρνήσεων", "refusals_total"), ("Άρνηση H", "refusal_H"),
            ("Επιβολές προστίμων", "impositions_total"), ("Εισπράξεις προστίμων", "payments_total"),
        ]
        for i, (label, key) in enumerate(auto_items):
            box = Card(); box.layout_box.addWidget(QLabel(label))
            val = QLabel("0"); val.setObjectName("Title"); box.layout_box.addWidget(val)
            self.auto_labels[key] = val
            grid.addWidget(box, 0, i)
        root.addWidget(auto)

        tabs = QTabWidget(); tabs.setObjectName("DailyTabs")

        def spin():
            w=QSpinBox(); w.setRange(0,99999); w.setButtonSymbols(QSpinBox.PlusMinus)
            return w

        def auto_card(title, fields):
            card=Card(); heading=QLabel(title); heading.setObjectName("SubTitle"); card.layout_box.addWidget(heading)
            form=QFormLayout(); form.setLabelAlignment(Qt.AlignLeft); form.setVerticalSpacing(9)
            for label,result_key,adjust_key in fields:
                w=spin(); self.auto_edit_inputs[result_key]=(w,adjust_key); form.addRow(label,w)
            card.layout_box.addLayout(form); return card

        def manual_card(index):
            group_title,fields=NUMERIC_GROUPS[index]
            card=Card(); heading=QLabel(group_title); heading.setObjectName("SubTitle"); card.layout_box.addWidget(heading)
            form=QFormLayout(); form.setLabelAlignment(Qt.AlignLeft); form.setVerticalSpacing(8)
            for label,key in fields:
                w=spin(); self.inputs[key]=w; form.addRow(label,w)
            card.layout_box.addLayout(form); return card

        # ΠΡΟΣΤΙΜΑ
        fines=QWidget(); fg=QGridLayout(fines); fg.setContentsMargins(12,12,12,12); fg.setSpacing(14)
        fg.addWidget(auto_card("ΕΠΙΒΟΛΕΣ",[
            ("Επιβολή 600 €","fine_imposition_600","adj_fine_imposition_600"),
            ("Επιβολή 1200 €","fine_imposition_1200","adj_fine_imposition_1200"),
        ]),0,0)
        fg.addWidget(auto_card("ΕΙΣΠΡΑΞΕΙΣ",[
            ("Είσπραξη 600 €","fine_payment_600","adj_fine_payment_600"),
            ("Είσπραξη 1200 €","fine_payment_1200","adj_fine_payment_1200"),
            ("eΠαράβολο 600 €","fine_eparavolo_600","adj_fine_eparavolo_600"),
            ("eΠαράβολο 1200 €","fine_eparavolo_1200","adj_fine_eparavolo_1200"),
            ("Δ.Ε. Τύπου-Α 600 €","fine_detypa_600","adj_fine_detypa_600"),
            ("Δ.Ε. Τύπου-Α 1200 €","fine_detypa_1200","adj_fine_detypa_1200"),
        ]),0,1)
        fg.setColumnStretch(0,1); fg.setColumnStretch(1,1)
        tabs.addTab(fines,"ΠΡΟΣΤΙΜΑ")

        # ΑΡΝΗΣΕΙΣ
        refs=QWidget(); rg=QGridLayout(refs); rg.setContentsMargins(12,12,12,12); rg.setSpacing(14)
        normal=[]
        for c in "ABCDEFGI":
            normal.append((f"Άρνηση ({c})",f"refusal_{c}",f"adj_refusal_{c}"))
        rg.addWidget(auto_card("ΛΟΓΟΙ ΑΡΝΗΣΗΣ",normal),0,0)
        hcard=Card(); hh=QLabel("SIS / Δ.Κ.Α."); hh.setObjectName("SubTitle"); hcard.layout_box.addWidget(hh)
        hf=QFormLayout(); hf.setLabelAlignment(Qt.AlignLeft); hf.setVerticalSpacing(8)
        for label,result_key,adjust_key in (
            ("Δ.Κ.Α. μόνο","h_dka_only","adj_h_dka_only"),
            ("S.I.S. μόνο","h_sis_only","adj_h_sis_only"),
            ("Δ.Κ.Α. και S.I.S.","h_both_only","adj_h_both_only"),
        ):
            w=spin(); self.auto_edit_inputs[result_key]=(w,adjust_key); hf.addRow(label,w)
        for label,key in (
            ("Δ.Κ.Α. με αλλαγή ονόματος","h_dka_name_change"),
            ("S.I.S. με αλλαγή ονόματος","h_sis_name_change"),
            ("Δ.Κ.Α. & S.I.S. με αλλαγή ονόματος","h_both_name_change"),
        ):
            w=spin(); self.inputs[key]=w; hf.addRow(label,w)
        hcard.layout_box.addLayout(hf); rg.addWidget(hcard,0,1)
        rg.setColumnStretch(0,1); rg.setColumnStretch(1,1)
        tabs.addTab(refs,"ΑΡΝΗΣΕΙΣ")

        # ΛΟΙΠΕΣ ΠΡΑΞΕΙΣ
        # A single scrolling work surface keeps every row at normal size.
        other=QWidget(); other_box=QVBoxLayout(other); other_box.setContentsMargins(8,8,8,8)
        other_scroll=QScrollArea(); other_scroll.setObjectName("OtherActsScroll")
        other_scroll.setWidgetResizable(True); other_scroll.setFrameShape(QScrollArea.NoFrame)
        other_content=QWidget(); og=QGridLayout(other_content); og.setContentsMargins(10,10,10,10); og.setSpacing(14)

        def full_manual_card(index):
            card=manual_card(index)
            field_count=len(NUMERIC_GROUPS[index][1])
            card.setMinimumHeight(max(230, 78 + field_count*43))
            return card

        for idx in range(5):
            og.addWidget(full_manual_card(idx),idx//2,idx%2)

        text_card=Card(); text_card.setMinimumHeight(220)
        text_card.layout_box.addWidget(QLabel("Στοιχεία συλλήψεων"))
        tf=QFormLayout(); tf.setVerticalSpacing(10)
        for label,key in TEXT_FIELDS:
            w=QLineEdit(); self.inputs[key]=w; tf.addRow(label,w)
        text_card.layout_box.addLayout(tf); og.addWidget(text_card,2,1)

        og.setColumnStretch(0,1); og.setColumnStretch(1,1)
        og.setRowStretch(3,1)
        other_scroll.setWidget(other_content); other_box.addWidget(other_scroll)
        tabs.addTab(other,"ΛΟΙΠΕΣ ΠΡΑΞΕΙΣ")

        root.addWidget(tabs,1)

        buttons = QHBoxLayout()
        save = QPushButton("ΑΠΟΘΗΚΕΥΣΗ"); save.clicked.connect(self.save)
        self.preview_btn = QPushButton("ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΤΡΕΧΟΥΣΑΣ ΑΝΑΦΟΡΑΣ"); self.preview_btn.setObjectName("Primary"); self.preview_btn.clicked.connect(self.preview)
        daily_archive = QPushButton("ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ"); daily_archive.clicked.connect(self.open_archive)
        buttons.addWidget(save); buttons.addStretch(1); buttons.addWidget(self.preview_btn); buttons.addWidget(daily_archive)
        root.addLayout(buttons)

    def _shift(self):
        return self.service.db.get_open_shift()

    def _report_shift(self):
        return self.service.db.get_current_or_last_shift()

    def _values(self):
        out = {}
        for key, w in self.inputs.items():
            if isinstance(w, QSpinBox): out[key] = w.value()
            elif isinstance(w, QLineEdit): out[key] = w.text().strip()

        shift=self._shift()
        if shift:
            auto=self.service.automatic_summary(int(shift["id"]))
            def baseline(result_key):
                if result_key=="h_dka_only":
                    return max(0,auto["h_dka_detected"]-int(out.get("h_dka_name_change",0)))
                if result_key=="h_sis_only":
                    return max(0,auto["h_sis_detected"]-int(out.get("h_sis_name_change",0)))
                if result_key=="h_both_only":
                    return max(0,auto["h_both_detected"]-int(out.get("h_both_name_change",0)))
                return int(auto.get(result_key,0))
            for result_key,(w,adjust_key) in self.auto_edit_inputs.items():
                out[adjust_key]=int(w.value())-baseline(result_key)
        return out

    def refresh(self):
        shift = self._shift()
        if not shift:
            self.shift_label.setText("Δεν υπάρχει ενεργή βάρδια.")
            self.preview_btn.setEnabled(bool(self._report_shift()))
            for label in self.auto_labels.values(): label.setText("0")
            for w in self.inputs.values(): w.setEnabled(False)
            for w,_ in self.auto_edit_inputs.values(): w.setEnabled(False)
            return
        self.preview_btn.setEnabled(True)
        for w in self.inputs.values(): w.setEnabled(True)
        for w,_ in self.auto_edit_inputs.values(): w.setEnabled(True)
        self.shift_label.setText(f"Αξιωματικός: {shift['officer_name']} · Έναρξη: {shift['started_at'].replace('T',' ')}")
        manual = self.service.get_manual(int(shift["id"]))
        for key, w in self.inputs.items():
            value = manual.get(key, 0 if isinstance(w, QSpinBox) else "")
            if isinstance(w, QSpinBox): w.setValue(int(value or 0))
            else: w.setText(str(value or ""))
        summary = self.service.summary_for_shift(int(shift["id"]))
        for key, label in self.auto_labels.items(): label.setText(str(summary.get(key, 0)))
        for result_key,(w,_) in self.auto_edit_inputs.items():
            w.setValue(int(summary.get(result_key,0) or 0))

    def save_current(self, *, quiet: bool = True) -> bool:
        shift = self._shift()
        if not shift:
            if not quiet: QMessageBox.warning(self, "Ημερήσια Δραστηριότητα", "Δεν υπάρχει ενεργή βάρδια.")
            return False
        try:
            self.service.save_manual(int(shift["id"]), self._values())
            if not quiet:
                self.refresh(); QMessageBox.information(self, "Ημερήσια Δραστηριότητα", "Τα στοιχεία αποθηκεύτηκαν.")
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Ημερήσια Δραστηριότητα", str(exc))
            return False

    def save(self):
        self.save_current(quiet=False)

    def preview(self):
        shift = self._report_shift()
        if not shift:
            QMessageBox.warning(self, "Ημερήσια Δραστηριότητα", "Δεν υπάρχει διαθέσιμη βάρδια για αναφορά."); return
        try:
            if shift["status"] == "OPEN":
                self.service.save_manual(int(shift["id"]), self._values())
            path = self.service.generate(int(shift["id"]), archive=False)
            self.service.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Ημερήσια Δραστηριότητα", str(exc))

    def open_reports_archive(self):
        self.actions.show_reports('DAILY')

    def open_archive(self):
        DailyArchiveDialog(self.service, self).exec()
