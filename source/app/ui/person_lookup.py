from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout
)


class PersonLookupDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.rows = []
        self.selected = None
        self.setWindowTitle("Αναζήτηση υπάρχοντος προσώπου")
        self.resize(980, 620)
        root = QVBoxLayout(self)
        info = QLabel("Αναζήτησε το πρόσωπο. Η επιλογή συμπληρώνει Επώνυμο, Όνομα, Ημ/νία γέννησης και το τελευταίο γνωστό διαβατήριο.")
        info.setWordWrap(True); root.addWidget(info)
        row = QHBoxLayout()
        self.surname = QLineEdit(); self.surname.setPlaceholderText("Επώνυμο")
        self.given = QLineEdit(); self.given.setPlaceholderText("Όνομα")
        self.birth = QLineEdit(); self.birth.setPlaceholderText("Ημ/νία γέννησης")
        row.addWidget(self.surname,2); row.addWidget(self.given,2); row.addWidget(self.birth,1); root.addLayout(row)
        opts = QHBoxLayout(); self.exact=QRadioButton("ΑΚΡΙΒΗΣ"); self.phonetic=QRadioButton("ΦΩΝΗΤΙΚΗ"); self.exact.setChecked(True)
        group=QButtonGroup(self); group.addButton(self.exact); group.addButton(self.phonetic)
        go=QPushButton("ΑΝΑΖΗΤΗΣΗ"); go.setObjectName("Primary"); go.clicked.connect(self.search)
        opts.addWidget(self.exact); opts.addWidget(self.phonetic); opts.addStretch(1); opts.addWidget(go); root.addLayout(opts)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["ΕΠΩΝΥΜΟ","ΟΝΟΜΑ","ΗΜ/ΝΙΑ ΓΕΝΝΗΣΗΣ","ΤΕΛ. ΔΙΑΒΑΤΗΡΙΟ","ΠΡΑΞΕΙΣ"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.choose); root.addWidget(self.table,1)
        actions=QHBoxLayout(); actions.addStretch(1); cancel=QPushButton("ΑΚΥΡΩΣΗ"); cancel.clicked.connect(self.reject); choose=QPushButton("ΧΡΗΣΗ ΣΤΟΙΧΕΙΩΝ"); choose.setObjectName("Primary"); choose.clicked.connect(self.choose); actions.addWidget(cancel); actions.addWidget(choose); root.addLayout(actions)
        for w in (self.surname,self.given,self.birth): w.returnPressed.connect(self.search)

    def search(self):
        if self.exact.isChecked():
            rows=self.db.search_people_exact(self.surname.text(),self.given.text(),self.birth.text())
        else:
            rows=self.db.search_people_phonetic(self.surname.text(),self.given.text())
        self.rows=list(rows); self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            prof=self.db.person_profile(int(x['id']))
            vals=[x['surname'],x['given_name'],x['birth_date'] or '',prof.get('passport_no',''),str(prof.get('actions_count',0))]
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self.table.resizeColumnsToContents()

    def choose(self):
        r=self.table.currentRow()
        if r<0 or r>=len(self.rows):
            QMessageBox.information(self,"Επιλογή","Επίλεξε πρώτα ένα πρόσωπο."); return
        x=self.rows[r]; prof=self.db.person_profile(int(x['id']))
        self.selected={"id":int(x['id']),"surname":x['surname'],"given_name":x['given_name'],"birth_date":x['birth_date'] or '',"passport_no":prof.get('passport_no','')}
        self.accept()
