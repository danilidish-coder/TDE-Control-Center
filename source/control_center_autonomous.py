from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from modules.app_config import AppConfig
from modules.app_service import AutonomousService, ProtocolDecisionRequired, resource_path
from modules.fines_engine import COLLECTION_METHODS, FineEntry
from modules.refusals_engine import REFUSAL_REASONS, RefusalEntry
from modules.refusal_languages import LANGUAGES
from modules.periodicals_engine import (
    IncompletePackageError, PROFILE_AS_IS, PROFILE_SAME_FOLDER, PROFILE_DAILY_FOLDER,
)
from modules.common import operational_date


def open_path(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if os.name == "nt":
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])


def run(argv=None) -> int:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
        QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
        QSpacerItem, QVBoxLayout, QWidget, QInputDialog, QListWidget,
    )

    APP_BG = "#eef3f7"
    NAVY = "#173d5d"
    NAVY_DARK = "#0d2940"
    TEAL = "#177d72"
    TEXT = "#153247"
    MUTED = "#667b8b"
    BORDER = "#d4e0e8"

    def line_edit(text: str = "", placeholder: str = "") -> QLineEdit:
        w = QLineEdit(text)
        w.setPlaceholderText(placeholder)
        w.setMinimumHeight(36)
        w.setStyleSheet(
            "QLineEdit{background:white;border:1px solid #c8d6e0;border-radius:8px;"
            "padding:6px 9px;font-size:12px;color:#173246;}"
            "QLineEdit:focus{border:2px solid #2b759c;}"
        )
        return w

    def combo(items=(), current: str = "") -> QComboBox:
        w = QComboBox()
        w.addItems(list(items))
        w.setMinimumHeight(36)
        w.setStyleSheet(
            "QComboBox{background:white;border:1px solid #c8d6e0;border-radius:8px;"
            "padding:5px 9px;font-size:12px;color:#173246;}"
        )
        if current:
            i = w.findText(current)
            if i >= 0:
                w.setCurrentIndex(i)
        return w

    class RaisedButton(QPushButton):
        def __init__(self, text: str, accent: str = NAVY, parent=None, *, compact=False):
            super().__init__(text, parent)
            self.setCursor(Qt.PointingHandCursor)
            self.setMinimumHeight(44 if compact else 76)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 5 if not compact else 3)
            self.setGraphicsEffect(shadow)
            self.setStyleSheet(f"""
                QPushButton {{
                    background:{accent}; color:white; border:none; border-radius:13px;
                    border-bottom:5px solid {NAVY_DARK};
                    padding:11px 16px; font-size:{'12' if compact else '17'}px; font-weight:800;
                }}
                QPushButton:hover {{ background:#245c80; }}
                QPushButton:pressed {{ border-bottom:1px solid {NAVY_DARK}; padding-top:15px; }}
            """)

    class SoftButton(QPushButton):
        def __init__(self, text: str, parent=None):
            super().__init__(text, parent)
            self.setCursor(Qt.PointingHandCursor)
            self.setMinimumHeight(36)
            self.setStyleSheet(
                "QPushButton{background:#f7fafc;border:1px solid #cbd8e1;border-radius:8px;"
                "padding:7px 12px;color:#31546d;font-weight:700;}"
                "QPushButton:hover{background:#eaf1f5;}"
            )

    class SectionTitle(QLabel):
        def __init__(self, text: str):
            super().__init__(text)
            self.setStyleSheet(f"font-size:15px;font-weight:900;color:{TEXT};padding-top:3px")

    class EntryDialog(QDialog):
        def __init__(self, parent, title: str, service: AutonomousService):
            super().__init__(parent)
            self.service = service
            self.setWindowTitle(title)
            self.setModal(True)
            self.setStyleSheet(f"QDialog{{background:{APP_BG};}} QLabel{{color:{TEXT};font-size:11px;}}")
            self.body = QVBoxLayout(self)
            self.body.setContentsMargins(22, 18, 22, 18)
            self.body.setSpacing(12)
            heading = QLabel(title)
            heading.setStyleSheet(f"font-size:20px;font-weight:900;color:{TEXT}")
            self.body.addWidget(heading)

        def error(self, exc: Exception):
            QMessageBox.critical(self, "Η διαδικασία δεν ολοκληρώθηκε", str(exc))

    class FineReportWindowDialog(QDialog):
        def __init__(self, parent, when: datetime | None = None):
            super().__init__(parent)
            self.setWindowTitle("ΝΕΑ ΑΝΑΦΟΡΑ ΠΡΟΣΤΙΜΩΝ")
            self.setModal(True)
            self.setStyleSheet(f"QDialog{{background:{APP_BG};}} QLabel{{color:{TEXT};font-size:11px;}}")
            now = when or datetime.now()
            op = operational_date(now)
            start = datetime(op.year, op.month, op.day, 10, 0)
            end = start + timedelta(days=1)
            lay = QVBoxLayout(self); lay.setContentsMargins(22,18,22,18); lay.setSpacing(12)
            title = QLabel("Νέα Αναφορά Προστίμων")
            title.setStyleSheet(f"font-size:18px;font-weight:900;color:{TEXT}")
            lay.addWidget(title)
            note = QLabel("Ελέγξτε την ημερομηνία και την ώρα. Μπορείτε να αλλάξετε και τα τέσσερα πεδία πριν δημιουργηθεί η νέα αναφορά.")
            note.setWordWrap(True); note.setStyleSheet(f"color:{MUTED};background:#e4edf3;border-radius:8px;padding:8px")
            lay.addWidget(note)
            form = QGridLayout(); form.setHorizontalSpacing(12); form.setVerticalSpacing(8)
            self.start_date = line_edit(start.strftime("%d/%m/%Y")); self.start_time = line_edit(start.strftime("%H:%M"))
            self.end_date = line_edit(end.strftime("%d/%m/%Y")); self.end_time = line_edit(end.strftime("%H:%M"))
            for r,(lab,w1,w2) in enumerate((("Από",self.start_date,self.start_time),("Έως",self.end_date,self.end_time))):
                form.addWidget(QLabel(lab),r,0);form.addWidget(w1,r,1);form.addWidget(w2,r,2)
            lay.addLayout(form)
            actions=QHBoxLayout();actions.addStretch()
            cancel=SoftButton("ΑΚΥΡΩΣΗ");cancel.clicked.connect(self.reject)
            create=RaisedButton("ΔΗΜΙΟΥΡΓΙΑ",TEAL,compact=True);create.setFixedWidth(180);create.clicked.connect(self._accept_checked)
            actions.addWidget(cancel);actions.addWidget(create);lay.addLayout(actions)
            self._window = None

        @staticmethod
        def _parse(date_text: str, time_text: str) -> datetime:
            return datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%d/%m/%Y %H:%M")

        def _accept_checked(self):
            try:
                start=self._parse(self.start_date.text(),self.start_time.text())
                end=self._parse(self.end_date.text(),self.end_time.text())
                if end <= start:
                    raise ValueError("Η λήξη πρέπει να είναι μετά την έναρξη.")
                self._window=(start,end);self.accept()
            except Exception as exc:
                QMessageBox.warning(self,"Έλεγχος ημερομηνίας/ώρας",str(exc))

        def selected_window(self):
            return self._window

    class VasReportWindowDialog(QDialog):
        def __init__(self, parent, when: datetime | None = None):
            super().__init__(parent)
            self.setWindowTitle("ΝΕΟ ΒΑΣ")
            self.setModal(True)
            self.setStyleSheet(f"QDialog{{background:{APP_BG};}} QLabel{{color:{TEXT};font-size:11px;}}")
            now = when or datetime.now()
            op = operational_date(now)
            start = datetime(op.year, op.month, op.day, 10, 0)
            end = start + timedelta(days=1)
            lay = QVBoxLayout(self); lay.setContentsMargins(22,18,22,18); lay.setSpacing(12)
            title = QLabel("Νέο ΒΑΣ Αρνήσεων")
            title.setStyleSheet(f"font-size:18px;font-weight:900;color:{TEXT}")
            lay.addWidget(title)
            note = QLabel("Ορίστε την πραγματική ημερομηνία και ώρα ανάληψης/λήξης της βάρδιας. Η 10:00 είναι μόνο προτεινόμενη τιμή.")
            note.setWordWrap(True); note.setStyleSheet(f"color:{MUTED};background:#e4edf3;border-radius:8px;padding:8px")
            lay.addWidget(note)
            form = QGridLayout(); form.setHorizontalSpacing(12); form.setVerticalSpacing(8)
            self.start_date = line_edit(start.strftime("%d/%m/%Y")); self.start_time = line_edit(start.strftime("%H:%M"))
            self.end_date = line_edit(end.strftime("%d/%m/%Y")); self.end_time = line_edit(end.strftime("%H:%M"))
            for r,(lab,w1,w2) in enumerate((("Από",self.start_date,self.start_time),("Έως",self.end_date,self.end_time))):
                form.addWidget(QLabel(lab),r,0);form.addWidget(w1,r,1);form.addWidget(w2,r,2)
            lay.addLayout(form)
            actions=QHBoxLayout();actions.addStretch()
            cancel=SoftButton("ΑΚΥΡΩΣΗ");cancel.clicked.connect(self.reject)
            create=RaisedButton("ΔΗΜΙΟΥΡΓΙΑ",TEAL,compact=True);create.setFixedWidth(180);create.clicked.connect(self._accept_checked)
            actions.addWidget(cancel);actions.addWidget(create);lay.addLayout(actions)
            self._window = None

        @staticmethod
        def _parse(date_text: str, time_text: str) -> datetime:
            return datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%d/%m/%Y %H:%M")

        def _accept_checked(self):
            try:
                start=self._parse(self.start_date.text(),self.start_time.text())
                end=self._parse(self.end_date.text(),self.end_time.text())
                if end <= start:
                    raise ValueError("Η λήξη πρέπει να είναι μετά την έναρξη.")
                self._window=(start,end);self.accept()
            except Exception as exc:
                QMessageBox.warning(self,"Έλεγχος ημερομηνίας/ώρας",str(exc))

        def selected_window(self):
            return self._window

    class FineDialog(EntryDialog):
        LABELS = (
            ("date", "Ημερομηνία"),
            ("imposition_protocol", "Αρ. πράξης επιβολής"),
            ("paravolo", "Αριθμός παραβόλου"),
            ("surname", "Επώνυμο"),
            ("name", "Όνομα"),
            ("birth_date", "Ημ/νία γέννησης"),
            ("nationality", "Υπηκοότητα"),
            ("passport", "Αρ. διαβατηρίου"),
            ("measure", "Αρ. μέτρου"),
            ("amount", "Χρηματικό ποσό"),
            ("collection_method", "Τρόπος είσπραξης"),
            ("collection_protocol", "Αριθμός πρωτοκόλλου"),
            ("responsible", "Αρμόδιος"),
        )

        def __init__(self, parent, service: AutonomousService, cfg: AppConfig):
            super().__init__(parent, "ΠΡΟΣΤΙΜΑ", service)
            self.cfg = cfg
            self.resize(800, 660)
            top_actions=QHBoxLayout()
            new_report=SoftButton("ΝΕΑ ΑΝΑΦΟΡΑ")
            new_report.clicked.connect(self._manual_new_report)
            top_actions.addWidget(new_report);top_actions.addStretch()
            self.body.addLayout(top_actions)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
            container = QWidget(); grid = QGridLayout(container); grid.setHorizontalSpacing(22); grid.setVerticalSpacing(9)
            self.fields = {}
            defaults = {
                "date": datetime.now().strftime("%d/%m/%Y"),
                "responsible": (cfg.officer_name.split()[0] if cfg.officer_name.strip() else ""),
            }
            for idx, (key, label) in enumerate(self.LABELS):
                col = 0 if idx < 7 else 2
                row = idx if idx < 7 else idx - 7
                lab = QLabel(label); lab.setStyleSheet(f"font-weight:700;color:{MUTED}")
                if key == "collection_method":
                    w = combo(("",) + COLLECTION_METHODS)
                elif key == "amount":
                    w = combo(("600", "1200"), "600")
                else:
                    w = line_edit(defaults.get(key, ""))
                self.fields[key] = w
                grid.addWidget(lab, row, col)
                grid.addWidget(w, row, col + 1)
            note = QLabel("Επιβολή = Αριθμός παραβόλου και Τρόπος είσπραξης κενά.  Η λογική αυτή είναι ίδια με το VBA.")
            note.setWordWrap(True); note.setStyleSheet(f"color:{MUTED};background:#e4edf3;border-radius:8px;padding:8px")
            grid.addWidget(note, 7, 0, 1, 4)
            scroll.setWidget(container); self.body.addWidget(scroll, 1)
            actions = QHBoxLayout(); actions.addStretch()
            save = RaisedButton("ΚΑΤΑΧΩΡΙΣΗ", TEAL, compact=True); save.setFixedWidth(230); save.clicked.connect(self._save)
            actions.addWidget(save); self.body.addLayout(actions)
            QTimer.singleShot(0, self._check_report_boundary)

        def _create_report_interactive(self) -> bool:
            dlg=FineReportWindowDialog(self)
            if dlg.exec() != QDialog.Accepted:
                return False
            start,end=dlg.selected_window()
            self.service.create_new_fine_report(start,end)
            QMessageBox.information(self,"Νέα Αναφορά",f"Δημιουργήθηκε νέα Αναφορά Προστίμων.\n\nΑπό: {start:%d/%m/%Y %H:%M}\nΈως: {end:%d/%m/%Y %H:%M}")
            return True

        def _manual_new_report(self):
            try:
                self._create_report_interactive()
            except Exception as exc:
                self.error(exc)

        def _check_report_boundary(self):
            try:
                now=datetime.now()
                if not self.service.fine_report_prompt_needed(now):
                    return
                exists=self.service.fine_live_report(now).exists()
                text=("Έχει αλλάξει η λειτουργική ημέρα. Θέλετε να δημιουργηθεί νέα Αναφορά Προστίμων;"
                      if exists else "Δεν υπάρχει ενεργή Αναφορά Προστίμων. Θέλετε να δημιουργηθεί τώρα;")
                ans=QMessageBox.question(self,"Αναφορά Προστίμων",text,QMessageBox.Yes|QMessageBox.No,QMessageBox.Yes)
                if ans==QMessageBox.Yes:
                    self._create_report_interactive()
                elif exists:
                    # Continue the existing report and do not ask again on every opening today.
                    self.service.mark_fine_report_prompted(now)
            except Exception as exc:
                self.error(exc)

        def _resolve_protocol_choice(self, e: FineEntry) -> bool:
            if e.is_imposition or not self.service.protocol_decision_needed(e.responsible):
                return True
            owner=self.service._protocol_owner_key(e.responsible)
            box=QMessageBox(self)
            box.setWindowTitle("Πρωτόκολλο πληρωμών")
            box.setIcon(QMessageBox.Question)
            box.setText(f"Υπάρχει ήδη Πρωτόκολλο για {owner}.")
            box.setInformativeText("Θέλετε να συνεχίσετε το υπάρχον ή να δημιουργηθεί νέο καθαρό Πρωτόκολλο;")
            cont=box.addButton("ΣΥΝΕΧΙΣΗ ΥΠΑΡΧΟΝΤΟΣ",QMessageBox.AcceptRole)
            new=box.addButton("ΔΗΜΙΟΥΡΓΙΑ ΝΕΟΥ",QMessageBox.DestructiveRole)
            cancel=box.addButton("ΑΚΥΡΩΣΗ",QMessageBox.RejectRole)
            box.exec()
            clicked=box.clickedButton()
            if clicked is cont:
                self.service.select_protocol_mode(e.responsible,create_new=False);return True
            if clicked is new:
                self.service.select_protocol_mode(e.responsible,create_new=True);return True
            return False

        def _v(self, key: str) -> str:
            w = self.fields[key]
            return w.currentText().strip() if isinstance(w, QComboBox) else w.text().strip()

        def _save(self):
            try:
                e = FineEntry(
                    date=self._v("date"), imposition_protocol=self._v("imposition_protocol"),
                    paravolo=self._v("paravolo"), surname=self._v("surname"), name=self._v("name"),
                    birth_date=self._v("birth_date"), nationality=self._v("nationality"), passport=self._v("passport"),
                    measure=self._v("measure"), amount=int(self._v("amount")), collection_method=self._v("collection_method"),
                    collection_protocol=self._v("collection_protocol"), responsible=self._v("responsible"),
                )
                e.validate()
                answer=QMessageBox.question(
                    self,"Επιβεβαίωση","Θέλετε να γίνει η καταχώριση;",
                    QMessageBox.Yes | QMessageBox.No,QMessageBox.No
                )
                if answer != QMessageBox.Yes:
                    return
                if not self.service.fine_live_report().exists():
                    if not self._create_report_interactive():
                        return
                if not self._resolve_protocol_choice(e):
                    return
                report = self.service.add_fine(e)
                ar=self.service.last_activity_result
                if ar.queued:
                    QMessageBox.warning(self, "Καταχώριση με εκκρεμότητα",
                        f"Η κύρια καταχώριση ολοκληρώθηκε.\n\nΑναφορά:\n{report}\n\n"
                        f"Η Ημερήσια Δραστηριότητα μπήκε σε ασφαλή εκκρεμότητα:\n{ar.error}")
                elif ar.error:
                    QMessageBox.warning(self,"Καταχώριση ολοκληρώθηκε",
                        f"Η κύρια καταχώριση ολοκληρώθηκε.\n\nΑναφορά:\n{report}\n\n"
                        f"Η Ημερήσια Δραστηριότητα δεν ενημερώθηκε:\n{ar.error}")
                else:
                    QMessageBox.information(self, "Ολοκληρώθηκε", f"Η καταχώριση ολοκληρώθηκε.\n\nΑναφορά:\n{report}")
                self.accept()
            except Exception as exc:
                self.error(exc)

    class RefusalDialog(EntryDialog):
        def __init__(self, parent, service: AutonomousService, cfg: AppConfig):
            super().__init__(parent, "ΑΡΝΗΣΗ ΕΙΣΟΔΟΥ", service)
            self.cfg = cfg; self.resize(910, 780)
            top_actions=QHBoxLayout()
            new_vas=SoftButton("ΝΕΟ ΒΑΣ")
            new_vas.clicked.connect(self._manual_new_vas)
            top_actions.addWidget(new_vas);top_actions.addStretch()
            self.body.addLayout(top_actions)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
            box = QWidget(); lay = QVBoxLayout(box); lay.setContentsMargins(4, 4, 12, 4); lay.setSpacing(12)
            self.fields = {}

            lay.addWidget(SectionTitle("Πρωτόκολλο"))
            pg = QGridLayout(); pg.setHorizontalSpacing(16); pg.setVerticalSpacing(7)
            proto = [
                ("aa", "Α/Α", cfg.refusal_aa), ("year", "Έτος", cfg.refusal_year),
                ("protocol_prefix", "Αρ. Πρωτοκόλλου", cfg.refusal_protocol_prefix),
                ("protocol_no", "Αριθμός", cfg.refusal_protocol_no),
            ]
            for i,(k,l,d) in enumerate(proto):
                pg.addWidget(QLabel(l), 0, i*2); w=line_edit(d); w.setMaximumWidth(150); self.fields[k]=w; pg.addWidget(w,0,i*2+1)
            lay.addLayout(pg)

            lay.addWidget(SectionTitle("Στοιχεία αλλοδαπού / άρνησης"))
            grid = QGridLayout(); grid.setHorizontalSpacing(18); grid.setVerticalSpacing(8)
            values = [
                ("date","Ημερομηνία",datetime.now().strftime("%d-%m-%Y")),
                ("time","Ώρα",datetime.now().strftime("%H:%M")),
                ("sex","Φύλο","M"),("surname","Επώνυμο",""),("name","Όνομα",""),
                ("birth_date","Ημ/νία γέννησης",""),("passport","Αρ. διαβατηρίου",""),
                ("issue_date","Ημ/νία έκδοσης",""),
            ]
            for i,(k,l,d) in enumerate(values):
                r=i%4; c=(i//4)*2; grid.addWidget(QLabel(l),r,c); w=line_edit(d); self.fields[k]=w; grid.addWidget(w,r,c+1)
            grid.addWidget(QLabel("Λόγος άρνησης"),4,0); reason=combo(REFUSAL_REASONS); reason.setMinimumWidth(520); self.fields["reason"]=reason; grid.addWidget(reason,4,1,1,3)
            grid.addWidget(QLabel("Γλώσσα εγγράφου"),5,0); language=combo(LANGUAGES,"ΑΛΒΑΝΙΚΑ"); language.setMinimumWidth(260); self.fields["language"]=language; grid.addWidget(language,5,1)
            lay.addLayout(grid)

            lay.addWidget(SectionTitle("Εθνικό μέτρο / SIS"))
            mg = QGridLayout(); mg.setHorizontalSpacing(18); mg.setVerticalSpacing(8)
            second = [
                ("measure_country","Αρχή εθν. μέτρου"),("measure_no","Αριθμός μέτρου"),
                ("measure_from","Έναρξη μέτρου"),("measure_to","Λήξη μέτρου"),
                ("sis_country","Αρχή SIS"),("sis_no","SIS"),
                ("sis_from","Έναρξη SIS"),("sis_to","Λήξη SIS"),
            ]
            for i,(k,l) in enumerate(second):
                r=i%4;c=(i//4)*2;mg.addWidget(QLabel(l),r,c);w=line_edit();self.fields[k]=w;mg.addWidget(w,r,c+1)
            lay.addLayout(mg)
            scroll.setWidget(box); self.body.addWidget(scroll,1)
            actions=QHBoxLayout();actions.addStretch();save=RaisedButton("ΚΑΤΑΧΩΡΙΣΗ / ΔΗΜΙΟΥΡΓΙΑ",TEAL,compact=True);save.setFixedWidth(290);save.clicked.connect(self._save);actions.addWidget(save);self.body.addLayout(actions)
            QTimer.singleShot(0, self._check_vas_boundary)

        def _create_vas_interactive(self) -> bool:
            dlg=VasReportWindowDialog(self)
            if dlg.exec() != QDialog.Accepted:
                return False
            start,end=dlg.selected_window()
            self.service.create_new_vas(start,end)
            QMessageBox.information(self,"Νέο ΒΑΣ",f"Δημιουργήθηκε νέο ΒΑΣ.\n\nΑπό: {start:%d/%m/%Y %H:%M}\nΈως: {end:%d/%m/%Y %H:%M}")
            return True

        def _manual_new_vas(self):
            try:
                self._create_vas_interactive()
            except Exception as exc:
                self.error(exc)

        def _check_vas_boundary(self):
            try:
                now=datetime.now()
                if not self.service.vas_prompt_needed(now):
                    return
                exists=self.service.vas_report().exists()
                text=("Έχει αλλάξει η λειτουργική ημέρα. Θέλετε να δημιουργηθεί νέο ΒΑΣ Αρνήσεων;"
                      if exists else "Δεν υπάρχει ενεργό ΒΑΣ Αρνήσεων. Θέλετε να δημιουργηθεί τώρα;")
                ans=QMessageBox.question(self,"ΒΑΣ Αρνήσεων",text,QMessageBox.Yes|QMessageBox.No,QMessageBox.Yes)
                if ans==QMessageBox.Yes:
                    self._create_vas_interactive()
                elif exists:
                    self.service.mark_vas_prompted(now)
            except Exception as exc:
                self.error(exc)

        def _v(self,key):
            w=self.fields[key]
            return w.currentText().strip() if isinstance(w,QComboBox) else w.text().strip()

        def _save(self):
            try:
                e=RefusalEntry(**{k:self._v(k) for k in (
                    "aa","year","protocol_prefix","protocol_no","date","time","sex","surname","name","birth_date",
                    "passport","issue_date","reason","measure_country","measure_no","measure_from","measure_to",
                    "sis_country","sis_no","sis_from","sis_to","language")})
                if not self.service.vas_report().exists():
                    if not self._create_vas_interactive():
                        return
                individual,vas=self.service.add_refusal(e)
                ar=self.service.last_activity_result
                if ar.queued:
                    QMessageBox.warning(self,"Καταχώριση με εκκρεμότητα",
                        f"Δημιουργήθηκαν:\n\n{individual}\n\n{vas}\n\n"
                        f"Η Ημερήσια Δραστηριότητα μπήκε σε ασφαλή εκκρεμότητα:\n{ar.error}")
                else:
                    QMessageBox.information(self,"Ολοκληρώθηκε",f"Δημιουργήθηκαν:\n\n{individual}\n\n{vas}")
                self.accept()
            except Exception as exc:self.error(exc)

    class PackageManagerDialog(EntryDialog):
        def __init__(self,parent,service:AutonomousService):
            super().__init__(parent,"ΔΙΑΧΕΙΡΙΣΗ ΠΑΚΕΤΩΝ",service);self.resize(760,560)
            note=QLabel("Αλλάζει μόνο η σύνθεση των πακέτων. Τα αρχικά Περιοδικά και οι αρχικοί φάκελοι δεν διαγράφονται ούτε μετακινούνται.")
            note.setWordWrap(True);note.setStyleSheet(f"color:{MUTED};background:#e4edf3;border-radius:8px;padding:10px")
            self.body.addWidget(note)
            self.body.addWidget(QLabel("Πακέτο"))
            self.pkg=combo();self.body.addWidget(self.pkg)
            self.files=QListWidget();self.files.setMinimumHeight(230);self.files.setStyleSheet(
                "QListWidget{background:white;border:1px solid #c8d6e0;border-radius:8px;padding:6px;color:#173246;font-size:12px;}"
                "QListWidget::item{padding:7px;} QListWidget::item:selected{background:#dbeaf3;color:#173246;}"
            );self.body.addWidget(self.files)
            row1=QHBoxLayout();
            for text,slot in (("ΝΕΟ ΠΑΚΕΤΟ",self._new_package),("ΜΕΤΟΝΟΜΑΣΙΑ",self._rename_package),("ΔΙΑΓΡΑΦΗ ΠΑΚΕΤΟΥ",self._delete_package)):
                b=SoftButton(text);b.clicked.connect(slot);row1.addWidget(b)
            self.body.addLayout(row1)
            row2=QHBoxLayout();add=RaisedButton("ΠΡΟΣΘΗΚΗ ΠΕΡΙΟΔΙΚΟΥ",TEAL,compact=True);rem=RaisedButton("ΑΦΑΙΡΕΣΗ ΠΕΡΙΟΔΙΚΟΥ",NAVY,compact=True)
            add.clicked.connect(self._add_file);rem.clicked.connect(self._remove_file);row2.addWidget(add);row2.addWidget(rem);self.body.addLayout(row2)
            close=SoftButton("ΚΛΕΙΣΙΜΟ");close.clicked.connect(self.accept);self.body.addWidget(close)
            self.pkg.currentIndexChanged.connect(self._refresh_files);self._reload()

        def _id(self):return str(self.pkg.currentData() or "")
        def _reload(self,select_id:str=""):
            old=select_id or self._id()
            self.engine,_,_=self.service.load_periodicals();self.pkg.blockSignals(True);self.pkg.clear()
            for p in self.engine.active_packages():self.pkg.addItem(p.name,p.id)
            if old:
                i=self.pkg.findData(old)
                if i>=0:self.pkg.setCurrentIndex(i)
            self.pkg.blockSignals(False);self._refresh_files()
        def _refresh_files(self):
            self.files.clear();pid=self._id()
            if not pid:return
            for f in self.engine.package_files(pid):
                item_text=f.name or Path(f.source_path).name
                from PySide6.QtWidgets import QListWidgetItem
                it=QListWidgetItem(item_text);it.setData(Qt.UserRole,f.source_path);it.setToolTip(f.source_path);self.files.addItem(it)

        def _new_package(self):
            name,ok=QInputDialog.getText(self,"Νέο πακέτο","Όνομα νέου πακέτου:")
            if not ok or not name.strip():return
            try:
                common_root=next((p.root for p in self.engine.active_packages() if p.root),"")
                if not common_root:
                    common_root=QFileDialog.getExistingDirectory(self,"Βασικός φάκελος πακέτων")
                    if not common_root:return
                pkg=self.service.create_periodical_package(name.strip(),common_root);self._reload(pkg.id)
            except Exception as exc:self.error(exc)

        def _rename_package(self):
            pid=self._id()
            if not pid:return
            current=self.engine.packages[pid].name
            name,ok=QInputDialog.getText(self,"Μετονομασία πακέτου","Νέο όνομα:",text=current)
            if not ok or not name.strip():return
            try:self.service.rename_periodical_package(pid,name.strip());self._reload(pid)
            except Exception as exc:self.error(exc)

        def _delete_package(self):
            pid=self._id()
            if not pid:return
            name=self.engine.packages[pid].name
            if QMessageBox.question(self,"Διαγραφή πακέτου",f"Να καταργηθεί το πακέτο «{name}»;\n\nΔεν θα διαγραφεί κανένα αρχικό Περιοδικό ή παλιός φάκελος.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            try:self.service.delete_periodical_package(pid);self._reload()
            except Exception as exc:self.error(exc)

        def _add_file(self):
            pid=self._id()
            if not pid:return
            try:
                catalog=self.service.periodical_catalog(pid)
                choices=[f"{f.name}   —   {f.source_path}" for f in catalog]
                choices.append("+ Νέο περιοδικό από αρχείο...")
                choice,ok=QInputDialog.getItem(self,"Προσθήκη Περιοδικού","Επιλέξτε Περιοδικό:",choices,0,False)
                if not ok:return
                idx=choices.index(choice)
                if idx < len(catalog):
                    self.service.add_known_periodical_to_package(pid,catalog[idx].source_path)
                else:
                    src,_=QFileDialog.getOpenFileName(self,"Επιλέξτε το τρέχον αρχείο του Περιοδικού")
                    if not src:return
                    labels=["ΩΣ ΕΧΕΙ","ΜΗΝΙΑΙΟ BAT (ΕΤΟΣ / ΜΗΝΑΣ)","ΗΜΕΡΗΣΙΟ BAT (ΕΤΟΣ / ΜΗΝΑΣ / ΗΜΕΡΑ)"]
                    label,ok=QInputDialog.getItem(self,"Τρόπος Περιοδικού","Πώς οργανώνεται το αρχείο;",labels,0,False)
                    if not ok:return
                    profile={labels[0]:PROFILE_AS_IS,labels[1]:PROFILE_SAME_FOLDER,labels[2]:PROFILE_DAILY_FOLDER}[label]
                    self.service.add_new_periodical_to_package(pid,src,profile)
                self._reload(pid)
            except Exception as exc:self.error(exc)

        def _remove_file(self):
            pid=self._id();it=self.files.currentItem()
            if not pid or it is None:return
            src=str(it.data(Qt.UserRole) or "");name=it.text()
            if QMessageBox.question(self,"Αφαίρεση Περιοδικού",f"Να αφαιρεθεί το «{name}» μόνο από αυτό το πακέτο;\n\nΤο αρχικό αρχείο δεν θα διαγραφεί.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            try:self.service.remove_periodical_from_package(pid,src);self._reload(pid)
            except Exception as exc:self.error(exc)

    class PeriodicalsDialog(EntryDialog):
        def __init__(self,parent,service:AutonomousService):
            super().__init__(parent,"ΠΕΡΙΟΔΙΚΑ",service);self.resize(720,430)
            engine,_,_=service.load_periodicals();self.engine=engine
            self.body.addWidget(QLabel("Πακέτο"))
            self.pkg=combo();
            for p in engine.active_packages():self.pkg.addItem(p.name,p.id)
            self.body.addWidget(self.pkg)
            details=QLabel("Η λογική ημερομηνιών, φακέλων, sharedfiles/scanfolder και επαναχρησιμοποίησης είναι η ίδια με το v10.3.")
            details.setWordWrap(True);details.setStyleSheet(f"color:{MUTED};background:#e4edf3;border-radius:8px;padding:10px");self.body.addWidget(details)
            self.info=QLabel("");self.info.setWordWrap(True);self.info.setStyleSheet(f"color:{TEXT};font-size:12px;padding:6px");self.body.addWidget(self.info)
            actions=QHBoxLayout();prep=RaisedButton("ΕΝΗΜΕΡΩΣΗ ΑΡΧΕΙΩΝ",TEAL,compact=True);ready=RaisedButton("ΕΤΟΙΜΟ ΠΑΚΕΤΟ",NAVY,compact=True)
            prep.clicked.connect(self._prepare);ready.clicked.connect(self._sync);actions.addWidget(prep);actions.addWidget(ready);self.body.addLayout(actions)
            small=SoftButton("Άνοιγμα πιο πρόσφατων");small.clicked.connect(self._open_latest);self.body.addWidget(small)
            manage=SoftButton("ΔΙΑΧΕΙΡΙΣΗ ΠΑΚΕΤΩΝ");manage.clicked.connect(self._manage);self.body.addWidget(manage);self.body.addStretch()
            self.pkg.currentIndexChanged.connect(self._refresh);self._refresh()

        def _id(self):return str(self.pkg.currentData() or "")
        def _reload_packages(self,select_id:str=""):
            current=select_id or self._id();self.engine,_,_=self.service.load_periodicals();self.pkg.blockSignals(True);self.pkg.clear()
            for p in self.engine.active_packages():self.pkg.addItem(p.name,p.id)
            if current:
                i=self.pkg.findData(current)
                if i>=0:self.pkg.setCurrentIndex(i)
            self.pkg.blockSignals(False);self._refresh()
        def _manage(self):
            current=self._id();PackageManagerDialog(self,self.service).exec();self._reload_packages(current)
        def _refresh(self):
            pid=self._id();
            if not pid:return
            p=self.engine.packages[pid];files=self.engine.package_files(pid)
            self.info.setText(f"{p.name}  •  {len(files)} ενεργά αρχεία\nΠρος: {p.to or '—'}\n{p.notes or ''}")
        def _prepare(self):
            try:
                r=self.service.prepare_periodical_package(self._id())
                msg=f"Ημερομηνία: {r.target_date:%d/%m/%Y}\nΔημιουργήθηκαν: {len(r.prepared)}\nΥπήρχαν ήδη: {len(r.skipped_existing)}"
                if r.failed:msg+=f"\nΧρειάζονται έλεγχο: {len(r.failed)}"
                QMessageBox.information(self,"Περιοδικά",msg)
            except Exception as exc:self.error(exc)
        def _sync(self):
            while True:
                try:
                    folder=self.service.sync_periodical_package(self._id())
                    QMessageBox.information(self,"Έτοιμο πακέτο",str(folder));open_path(folder);return
                except IncompletePackageError as exc:
                    details=[]
                    if exc.missing: details.append("Δεν βρέθηκαν:\n• " + "\n• ".join(exc.missing))
                    if exc.failed: details.append("Δεν αντιγράφηκαν μετά από 3 προσπάθειες:\n• " + "\n• ".join(exc.failed))
                    choice=QMessageBox.warning(
                        self,"Ελλιπές πακέτο - " + exc.package_name,
                        "Το πακέτο δεν ενημερώθηκε πλήρως.\n\n" + "\n\n".join(details) +
                        "\n\nΕΠΑΝΑΛΗΨΗ = ξαναδοκιμάζει όλο το πακέτο."
                        "\nΠΑΡΑΒΛΕΨΗ = συνεχίζει με τα υπόλοιπα αρχεία."
                        "\nΜΑΤΑΙΩΣΗ = σταματά χωρίς αποστολή.",
                        QMessageBox.Retry | QMessageBox.Ignore | QMessageBox.Abort,QMessageBox.Retry)
                    if choice == QMessageBox.Retry:
                        continue
                    if choice == QMessageBox.Ignore:
                        QMessageBox.warning(self,"Συνέχεια με ελλιπές πακέτο",
                            f"Ενημερώθηκαν: {exc.copied} από {exc.active} ενεργά αρχεία.\n\nΕλέγξτε τον μόνιμο φάκελο πριν την αποστολή.")
                        open_path(exc.folder)
                    return
                except Exception as exc:
                    self.error(exc);return
        def _open_latest(self):
            try:
                paths=self.service.latest_periodical_paths(self._id())
                if not paths:raise FileNotFoundError("Δεν υπάρχει ακόμη πρόσφατο αρχείο. Πατήστε πρώτα ΕΝΗΜΕΡΩΣΗ ΑΡΧΕΙΩΝ.")
                for p in paths:open_path(p)
            except Exception as exc:self.error(exc)

    class SettingsDialog(QDialog):
        def __init__(self,parent,cfg:AppConfig,on_saved):
            super().__init__(parent);self.cfg=cfg;self.on_saved=on_saved;self.setWindowTitle("Ρυθμίσεις");self.resize(770,260);self.setStyleSheet(f"QDialog{{background:{APP_BG};}}")
            main=QVBoxLayout(self);main.setContentsMargins(22,18,22,18);main.setSpacing(10)
            title=QLabel("ΡΥΘΜΙΣΕΙΣ");title.setStyleSheet(f"font-size:20px;font-weight:900;color:{TEXT}");main.addWidget(title)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);box=QWidget();form=QFormLayout(box);form.setSpacing(9);self.f={}
            def add(k,label,value,browse=None):
                if browse:
                    wrap=QWidget();h=QHBoxLayout(wrap);h.setContentsMargins(0,0,0,0);w=line_edit(value)
                    caption="ΕΠΙΛΟΓΗ" if browse=="excel" else "…"
                    b=SoftButton(caption);b.setFixedWidth(92 if browse=="excel" else 42);b.clicked.connect(lambda _=False,kk=k,mode=browse:self._browse(kk,mode));h.addWidget(w,1);h.addWidget(b);self.f[k]=w;form.addRow(label,wrap)
                else:
                    w=line_edit(value);self.f[k]=w;form.addRow(label,w)
            add("activity_workbook","Ημερήσια Δραστηριότητα (Excel)",cfg.activity_workbook,"excel")
            scroll.setWidget(box);main.addWidget(scroll,1)
            save=RaisedButton("ΑΠΟΘΗΚΕΥΣΗ",TEAL,compact=True);save.clicked.connect(self._save);main.addWidget(save)
        def _browse(self,k,mode):
            if mode=="folder":p=QFileDialog.getExistingDirectory(self,"Επιλογή φακέλου",self.f[k].text() or str(Path.home()))
            elif mode=="excel":p,_=QFileDialog.getOpenFileName(self,"Επιλογή Excel","","Excel (*.xlsx *.xlsm *.xlsb *.xls)")
            else:p,_=QFileDialog.getOpenFileName(self,"Επιλογή JSON","","JSON (*.json)")
            if p:self.f[k].setText(p)
        def _save(self):
            for k,w in self.f.items():setattr(self.cfg,k,w.text().strip())
            self.cfg.save();self.on_saved();self.accept()

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__();self.cfg=AppConfig.load();self.service=AutonomousService(self.cfg)
            self.setWindowTitle("Κέντρο Ελέγχου Αυτοματισμών - Τ.Δ.Ε. Κρυσταλλοπηγής");self.resize(900,650);self.setMinimumSize(760,570)
            logo=resource_path("police_emblem.jpeg")
            if logo.exists():self.setWindowIcon(QIcon(str(logo)))
            self._build()
        def _build(self):
            root=QWidget();root.setStyleSheet(f"background:{APP_BG};");self.setCentralWidget(root);lay=QVBoxLayout(root);lay.setContentsMargins(28,24,28,24);lay.setSpacing(18)
            head=QFrame();head.setStyleSheet(f"QFrame{{background:white;border:1px solid {BORDER};border-radius:18px;}}");hl=QHBoxLayout(head);hl.setContentsMargins(20,15,20,15);hl.setSpacing(17)
            logo=QLabel();logo.setFixedSize(76,76);logo.setAlignment(Qt.AlignCenter);lp=resource_path("police_emblem.jpeg")
            if lp.exists():logo.setPixmap(QPixmap(str(lp)).scaled(70,70,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            hl.addWidget(logo);t=QVBoxLayout();t.setSpacing(1)
            for text,style in [
                ("ΕΛΛΗΝΙΚΗ ΑΣΤΥΝΟΜΙΑ",f"font-size:12px;font-weight:900;color:{NAVY};letter-spacing:1px"),
                ("Τ.Δ.Ε. ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ",f"font-size:23px;font-weight:900;color:{TEXT}"),
                ("ΚΕΝΤΡΟ ΕΛΕΓΧΟΥ ΑΥΤΟΜΑΤΙΣΜΩΝ",f"font-size:14px;font-weight:800;color:{MUTED}"),
                ("ΑΝΘ/ΜΟΣ ΔΑΝΙΗΛΙΔΗΣ ΗΡΑΚΛΗΣ   •   ΑΝΘ/ΜΟΣ ΚΛΙΑΝΗΣ ΧΡΗΣΤΟΣ",f"font-size:10px;color:{MUTED}"),
            ]:
                x=QLabel(text);x.setStyleSheet(style);t.addWidget(x)
            hl.addLayout(t,1);settings=SoftButton("ΡΥΘΜΙΣΕΙΣ");settings.clicked.connect(self._settings);hl.addWidget(settings,0,Qt.AlignTop);lay.addWidget(head)
            card=QFrame();card.setStyleSheet(f"QFrame{{background:white;border:1px solid {BORDER};border-radius:18px;}}");cl=QVBoxLayout(card);cl.setContentsMargins(35,28,35,28);cl.setSpacing(18)
            intro=QLabel("Επιλέξτε εργασία");intro.setAlignment(Qt.AlignCenter);intro.setStyleSheet(f"font-size:16px;font-weight:900;color:{TEXT}");cl.addWidget(intro)
            b1=RaisedButton("ΠΡΟΣΤΙΜΑ",NAVY);b2=RaisedButton("ΑΡΝΗΣΕΙΣ ΕΙΣΟΔΟΥ",NAVY);b3=RaisedButton("ΠΕΡΙΟΔΙΚΑ",NAVY)
            b1.clicked.connect(self._fine);b2.clicked.connect(self._refusal);b3.clicked.connect(self._periodicals)
            for b in (b1,b2,b3):cl.addWidget(b)
            folders=QHBoxLayout();folders.setSpacing(10)
            f1=SoftButton("ΦΑΚΕΛΟΣ ΠΡΟΣΤΙΜΩΝ");f2=SoftButton("ΦΑΚΕΛΟΣ ΑΡΝΗΣΕΩΝ")
            f1.clicked.connect(self._open_fines_folder);f2.clicked.connect(self._open_refusals_folder)
            folders.addWidget(f1);folders.addWidget(f2);cl.addLayout(folders)
            lay.addWidget(card,1)
            status=QLabel("Αυτόνομη εφαρμογή • καθρεφτισμός της επιβεβαιωμένης λογικής VBA • λειτουργική ημέρα 10:00")
            status.setAlignment(Qt.AlignCenter);status.setStyleSheet(f"background:#dfeaf1;border-radius:9px;padding:8px;color:{MUTED};font-size:10px");lay.addWidget(status)
        def _reload(self):self.cfg=AppConfig.load();self.service=AutonomousService(self.cfg)
        def _settings(self):SettingsDialog(self,self.cfg,self._reload).exec()
        def _fine(self):FineDialog(self,self.service,self.cfg).exec()
        def _refusal(self):RefusalDialog(self,self.service,self.cfg).exec()
        def _open_fines_folder(self):
            try:open_path(self.service.fines_dir)
            except Exception as exc:QMessageBox.critical(self,"Φάκελος Προστίμων",str(exc))
        def _open_refusals_folder(self):
            try:open_path(self.service.refusal_dir)
            except Exception as exc:QMessageBox.critical(self,"Φάκελος Αρνήσεων",str(exc))
        def _periodicals(self):
            try:PeriodicalsDialog(self,self.service).exec()
            except Exception as exc:QMessageBox.critical(self,"Περιοδικά",str(exc))

    app=QApplication.instance() or QApplication(list(argv or sys.argv));app.setStyle("Fusion");w=MainWindow();w.show();return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
