"""Shift dialogs and status presentation, with the original interaction order."""
from PySide6.QtWidgets import QMessageBox
from app.features.shifts.dialogs import StartShiftDialog


class ShiftController:
    def __init__(self, view, workflow):
        self.view = view
        self.workflow = workflow

    def refresh_shift(self):
        row=self.view.db.get_open_shift()
        if row:
            self.view.shift_status.setText("● ΕΝΕΡΓΗ ΒΑΡΔΙΑ"); self.view.shift_status.setObjectName("StatusOpen")
            identity = " · ".join(x for x in (row["officer_rank_full"], row["officer_agms"], row["officer_name"]) if x)
            self.view.shift_detail.setText(f"{identity}\nΈναρξη: {row['started_at'].replace('T',' ')}")
        else:
            self.view.shift_status.setText("○ ΧΩΡΙΣ ΕΝΕΡΓΗ ΒΑΡΔΙΑ"); self.view.shift_status.setObjectName("StatusClosed")
            self.view.shift_detail.setText("Δεν έχει ξεκινήσει βάρδια.")
        self.view.start_btn.setEnabled(row is None)
        self.view.close_btn.setEnabled(row is not None)
        self.view.shift_status.style().unpolish(self.view.shift_status); self.view.shift_status.style().polish(self.view.shift_status)

    def start_shift(self):
        dlg=StartShiftDialog(self.view)
        if dlg.exec():
            try:
                officer_name = f"{dlg.surname.text().strip()} {dlg.name.text().strip()}".strip()
                self.workflow.start_shift(
                    officer_name,
                    officer_agms=dlg.agms.text(),
                    officer_rank_short=dlg.rank.text(),
                    officer_rank_full=dlg.rank.text(),
                ); self.view.refresh_shift()
                for name in ("fines","refusals","daily"): self.view.pages[name].refresh()
            except Exception as e: QMessageBox.warning(self.view,"Έναρξη βάρδιας",str(e))

    def close_shift(self):
        if QMessageBox.question(self.view,"Κλείσιμο βάρδιας","Να κλείσει η ενεργή βάρδια;") != QMessageBox.Yes: return
        try:
            shift = self.view.db.get_open_shift()
            if not shift:
                raise ValueError("Δεν υπάρχει ενεργή βάρδια.")
            if not self.view.pages["daily"].save_current(quiet=True):
                return
            shift_id, result = self.workflow.close_shift()
            self.view.refresh_shift()
            self.view.refresh_pending()
            self.view.pages["fines"].refresh()
            self.view.pages["refusals"].refresh()
            self.view.pages["daily"].refresh()
            if result.failed:
                details = "\n".join(f"• {self.view.pending.label(t)}: {err}" for t, err in result.failed)
                QMessageBox.warning(
                    self.view, "Κλείσιμο βάρδιας",
                    "Η βάρδια έκλεισε και τα δεδομένα αποθηκεύτηκαν. "
                    "Οι παρακάτω ενημερώσεις έμειναν σε εκκρεμότητα:\n\n" + details
                )
            else:
                QMessageBox.information(
                    self.view, "Κλείσιμο βάρδιας",
                    "Η βάρδια έκλεισε και οι αναφορές αρχειοθετήθηκαν.\n\n"
                    "Πρόστιμα: ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ\n"
                    "Αρνήσεις: ΑΡΧΕΙΟ ΒΑΣ\n"
                    "Ημερήσια: ΣΤΑΤΙΣΤΙΚΑ / ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ."
                )
        except Exception as e: QMessageBox.warning(self.view,"Κλείσιμο βάρδιας",str(e))
