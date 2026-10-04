from __future__ import annotations
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup,QHBoxLayout,QLabel,QLineEdit,QPushButton,QRadioButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from app.core.db import Database
from app.ui.widgets import Card

class PersonArchivePage(QWidget):
    useInFines=Signal(object)
    useInRefusals=Signal(object)
    def __init__(self,db:Database,parent=None):
        super().__init__(parent); self.db=db; self._people=[]; self._build()
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(10)
        head=Card(); title=QLabel('ΑΡΧΕΙΟ — ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ'); title.setObjectName('Title'); head.layout_box.addWidget(title)
        info=QLabel('ΑΚΡΙΒΗΣ: ψάχνει τα στοιχεία όπως έχουν καταχωριστεί. ΦΩΝΗΤΙΚΗ: εμφανίζει πιθανά παρόμοια ονόματα. Επίλεξε το σωστό πρόσωπο για να δεις το ιστορικό του ή να χρησιμοποιήσεις τα στοιχεία του στα Πρόστιμα / Αρνήσεις.'); info.setWordWrap(True); head.layout_box.addWidget(info); root.addWidget(head)
        tools=Card(); row=QHBoxLayout(); self.surname=QLineEdit(); self.surname.setPlaceholderText('Επώνυμο'); self.given=QLineEdit(); self.given.setPlaceholderText('Όνομα'); self.birth=QLineEdit(); self.birth.setPlaceholderText('Ημ/νία γέννησης'); row.addWidget(self.surname,2); row.addWidget(self.given,2); row.addWidget(self.birth,1); tools.layout_box.addLayout(row)
        opts=QHBoxLayout(); self.exact=QRadioButton('ΑΚΡΙΒΗΣ'); self.phonetic=QRadioButton('ΦΩΝΗΤΙΚΗ'); self.exact.setChecked(True); grp=QButtonGroup(self); grp.addButton(self.exact); grp.addButton(self.phonetic); search=QPushButton('ΑΝΑΖΗΤΗΣΗ'); search.setObjectName('Primary'); search.clicked.connect(self.run_search); opts.addWidget(self.exact); opts.addWidget(self.phonetic); opts.addStretch(1); opts.addWidget(search); tools.layout_box.addLayout(opts); root.addWidget(tools)
        self.people_table=QTableWidget(0,5); self.people_table.setHorizontalHeaderLabels(['ΕΠΩΝΥΜΟ','ΟΝΟΜΑ','ΗΜ/ΝΙΑ ΓΕΝΝΗΣΗΣ','ΤΕΛ. ΔΙΑΒΑΤΗΡΙΟ','ΠΡΑΞΕΙΣ']); self.people_table.setSelectionBehavior(QTableWidget.SelectRows); self.people_table.setEditTriggers(QTableWidget.NoEditTriggers); self.people_table.itemSelectionChanged.connect(self.load_history); self.people_table.itemSelectionChanged.connect(self._sync_action_buttons); root.addWidget(self.people_table,2)
        actions=QHBoxLayout(); actions.addStretch(1)
        self.use_fines_btn=QPushButton('ΧΡΗΣΗ ΣΤΑ ΠΡΟΣΤΙΜΑ'); self.use_fines_btn.setObjectName('Primary'); self.use_fines_btn.setEnabled(False); self.use_fines_btn.clicked.connect(lambda: self._emit(self.useInFines))
        self.use_refusals_btn=QPushButton('ΧΡΗΣΗ ΣΤΙΣ ΑΡΝΗΣΕΙΣ'); self.use_refusals_btn.setObjectName('Primary'); self.use_refusals_btn.setEnabled(False); self.use_refusals_btn.clicked.connect(lambda: self._emit(self.useInRefusals))
        actions.addWidget(self.use_fines_btn); actions.addWidget(self.use_refusals_btn); root.addLayout(actions)
        root.addWidget(QLabel('ΙΣΤΟΡΙΚΟ ΠΡΑΞΕΩΝ'))
        self.history=QTableWidget(0,6); self.history.setHorizontalHeaderLabels(['ΗΜΕΡΟΜΗΝΙΑ','ΠΡΑΞΗ','ΛΟΓΟΣ','ΔΙΑΒΑΤΗΡΙΟ','ΠΡΩΤΟΚΟΛΛΟ','ΣΤΟΙΧΕΙΑ']); self.history.setEditTriggers(QTableWidget.NoEditTriggers); root.addWidget(self.history,3)
        for w in (self.surname,self.given,self.birth): w.returnPressed.connect(self.run_search)
    def run_search(self):
        rows=self.db.search_people_exact(self.surname.text(),self.given.text(),self.birth.text()) if self.exact.isChecked() else self.db.search_people_phonetic(self.surname.text(),self.given.text()); self._people=list(rows); self.people_table.setRowCount(len(self._people))
        for r,x in enumerate(self._people):
            prof=self.db.person_profile(int(x['id'])); vals=[x['surname'],x['given_name'],x['birth_date'] or '',prof.get('passport_no',''),str(prof.get('actions_count',0))]
            for c,v in enumerate(vals): self.people_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.people_table.resizeColumnsToContents(); self.history.setRowCount(0); self._sync_action_buttons()
    def _selected(self):
        r=self.people_table.currentRow()
        if r<0 or r>=len(self._people): return None
        x=self._people[r]; return self.db.person_profile(int(x['id']))
    def _sync_action_buttons(self):
        enabled=self._selected() is not None
        self.use_fines_btn.setEnabled(enabled)
        self.use_refusals_btn.setEnabled(enabled)
    def _emit(self,signal):
        x=self._selected()
        if x: signal.emit(x)
    def _details(self,raw):
        try: d=json.loads(raw or '{}')
        except Exception: return str(raw or '')
        labels={'amount':'Ποσό','collector':'Αστυνομικός / Αρμόδιος','receipt_list_id':'Λίστα','measure':'Μέτρο','paravolo':'Παράβολο','language':'Γλώσσα'}
        parts=[]
        for k,v in d.items():
            if v not in ('',None,[],{}): parts.append(f"{labels.get(k,k)}: {v}")
        return ' | '.join(parts)
    def load_history(self):
        x=self._selected()
        if not x:return
        rows=self.db.person_history(int(x['id'])); self.history.setRowCount(len(rows)); action_names={'REFUSAL':'ΑΡΝΗΣΗ','FINE_IMPOSITION':'ΕΠΙΒΟΛΗ ΠΡΟΣΤΙΜΟΥ','PAYMENT':'ΕΙΣΠΡΑΞΗ ΠΡΟΣΤΙΜΟΥ'}
        for rr,row in enumerate(rows):
            vals=[str(row['occurred_at']).replace('T',' '),action_names.get(row['action_type'],row['action_type']),row['reason'] or '',row['passport_no'] or '',row['protocol_no'] or '',self._details(row['details_json'])]
            for c,v in enumerate(vals): self.history.setItem(rr,c,QTableWidgetItem(str(v)))
        self.history.resizeColumnsToContents()
