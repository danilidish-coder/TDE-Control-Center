from __future__ import annotations

import os
from app.services.pdf_preview import open_document_preview
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox,QDialog,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout
from app.docgen.refusals import REFUSAL_REASONS
from app.services.refusals import RefusalService

class RefusalsArchiveDialog(QDialog):
    def __init__(self, service: RefusalService, parent=None):
        super().__init__(parent); self.service=service
        self.setWindowTitle('ΑΡΧΕΙΟ ΑΡΝΗΣΕΩΝ'); self.resize(1180,680)
        root=QVBoxLayout(self)
        t=QLabel('ΑΡΧΕΙΟ ΑΡΝΗΣΕΩΝ — ΑΝΑΖΗΤΗΣΗ'); t.setObjectName('Title'); root.addWidget(t)
        row=QHBoxLayout(); self.q=QLineEdit(); self.q.setPlaceholderText('Επώνυμο, όνομα, διαβατήριο ή πρωτόκολλο'); self.q.returnPressed.connect(self.refresh)
        self.reason=QComboBox(); self.reason.addItem('ΟΛΟΙ ΟΙ ΛΟΓΟΙ',''); [self.reason.addItem(x,x) for x in REFUSAL_REASONS]; self.reason.currentIndexChanged.connect(self.refresh)
        b=QPushButton('ΑΝΑΖΗΤΗΣΗ'); b.setObjectName('Primary'); b.clicked.connect(self.refresh)
        row.addWidget(self.q,1); row.addWidget(self.reason); row.addWidget(b); root.addLayout(row)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels(['Ημερομηνία/ώρα','Επώνυμο','Όνομα','Διαβατήριο','Λόγος','Α/Α','Πρωτόκολλο','Γλώσσα','Αξ. Υπηρεσίας']); self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection); self.table.setAlternatingRowColors(True); self.table.horizontalHeader().setStretchLastSection(True); root.addWidget(self.table,1)
        br=QHBoxLayout(); br.addStretch(1)
        e=QPushButton('ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ'); e.clicked.connect(self.edit_selected)
        d=QPushButton('ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ'); d.clicked.connect(self.delete_selected)
        p=QPushButton('ΑΝΟΙΓΜΑ ΕΠΙΛΕΓΜΕΝΗΣ ΑΡΝΗΣΗΣ'); p.clicked.connect(self.preview)
        v=QPushButton('ΑΝΟΙΓΜΑ / ΕΚΤΥΠΩΣΗ ΒΑΣ ΒΑΡΔΙΑΣ'); v.clicked.connect(self.open_shift_vas)
        c=QPushButton('ΚΛΕΙΣΙΜΟ'); c.clicked.connect(self.accept)
        for w in (e,d,p,v,c): br.addWidget(w)
        root.addLayout(br); self.refresh()
    def refresh(self):
        rows=self.service.search_refusals(self.q.text(),self.reason.currentData()); self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[(row['occurred_at'] or '').replace('T',' '),row['surname'] or '',row['given_name'] or '',row['passport_no'] or '',row['reason'] or '',f"{row['aa']}/{row['refusal_year']}",f"{row['protocol_prefix']}/{row['protocol_no']}",row['language'] or '',row['officer_name'] or '']
            for c,v in enumerate(vals):
                it=QTableWidgetItem(v); it.setData(Qt.UserRole,(int(row['id']),int(row['shift_id']))); self.table.setItem(r,c,it)
        self.table.resizeColumnsToContents()
    def _selected_ids(self):
        r=self.table.currentRow()
        if r<0:
            QMessageBox.information(self,'Αρχείο Αρνήσεων','Επίλεξε πρώτα μία καταχώριση.'); return None
        return self.table.item(r,0).data(Qt.UserRole)

    def edit_selected(self):
        selected=self._selected_ids()
        if not selected:return
        refusal_id,_=selected
        parent=self.parent()
        if parent is None or not hasattr(parent,'begin_edit'):
            QMessageBox.warning(self,'Διόρθωση Άρνησης','Δεν είναι διαθέσιμη η φόρμα διόρθωσης.'); return
        try:
            parent.begin_edit(int(refusal_id)); self.accept()
        except Exception as exc: QMessageBox.warning(self,'Διόρθωση Άρνησης',str(exc))

    def delete_selected(self):
        selected=self._selected_ids()
        if not selected:return
        refusal_id,_=selected
        try:
            row=self.service.get_refusal(int(refusal_id))
            if row is None: raise ValueError('Δεν βρέθηκε η επιλεγμένη άρνηση.')
            entry=self.service._row_to_entry(row)
            person=(f"{row['surname']} {row['given_name']}").strip()
            if QMessageBox.question(self,'Επιβεβαίωση διαγραφής',f"Να διαγραφεί οριστικά η άρνηση;\n\n{person} — {row['refusal_date']}\n\nΘα ενημερωθούν η ατομική άρνηση, το ΒΑΣ και η Ημερήσια Δραστηριότητα της βάρδιας.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            result=self.service.delete_refusal(int(refusal_id),expected_entry=entry)
            self.refresh()
            parent=self.parent()
            if parent is not None and hasattr(parent,'refresh'): parent.refresh()
            mw=parent.window() if parent is not None else self.window()
            if hasattr(mw,'pages'):
                for name in ('daily','reports'):
                    page=mw.pages.get(name)
                    if page is not None and hasattr(page,'refresh'): page.refresh()
            if hasattr(mw,'refresh_pending'): mw.refresh_pending()
            if result.failed:
                from app.services.pending import PendingService
                details='\n'.join(f'• {PendingService.label(t)}: {error}' for t,error in result.failed)
                QMessageBox.warning(self,'Η άρνηση διαγράφηκε','Η άρνηση διαγράφηκε από τα δεδομένα. Οι παρακάτω ενημερώσεις αρχείων έμειναν σε εκκρεμότητα:\n\n'+details)
            else: QMessageBox.information(self,'Ολοκληρώθηκε','Η άρνηση διαγράφηκε και όλα τα συνδεδεμένα αρχεία ενημερώθηκαν.')
        except Exception as exc: QMessageBox.warning(self,'Διαγραφή Άρνησης',str(exc))

    def preview(self):
        r=self.table.currentRow()
        if r<0: QMessageBox.information(self,'Αρχείο Αρνήσεων','Επίλεξε πρώτα μία καταχώριση.'); return
        try:
            refusal_id,_=self.table.item(r,0).data(Qt.UserRole)
            p=self.service.generate_individual_from_id(int(refusal_id))
            if os.name=='nt': open_document_preview(p)
            else: QMessageBox.information(self,'Προεπισκόπηση',str(p))
        except Exception as exc: QMessageBox.warning(self,'Αρχείο Αρνήσεων',str(exc))
    def open_shift_vas(self):
        r=self.table.currentRow()
        if r<0:
            QMessageBox.information(self,'Αρχείο Αρνήσεων','Επίλεξε πρώτα μία καταχώριση.'); return
        try:
            _,shift_id=self.table.item(r,0).data(Qt.UserRole)
            p=self.service.generate_vas(int(shift_id),archive=True)
            if not p: raise ValueError('Δεν υπάρχουν αρνήσεις στη συγκεκριμένη βάρδια.')
            if os.name=='nt': open_document_preview(p)
            else: QMessageBox.information(self,'ΒΑΣ Βάρδιας',str(p))
        except Exception as exc: QMessageBox.warning(self,'Αρχείο Αρνήσεων',str(exc))
