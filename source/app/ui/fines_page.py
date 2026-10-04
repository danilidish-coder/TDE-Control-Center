from __future__ import annotations
import os
from app.services.pdf_preview import open_document_preview
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox,QGridLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from app.docgen.fines_report import FineEntry,COLLECTION_METHODS
from app.services.fines import FineService
from app.ui.widgets import Card
from app.ui.fines_archive import FinesArchiveDialog
from app.ui.history_autocomplete import install_history_completer

class FinesPage(QWidget):
    def __init__(self,service:FineService,parent=None):
        super().__init__(parent); self.service=service; self._editing_id=None; self._editing_shift=None; self._original_entry=None; self._build(); self.refresh()
    def _label(self,text):
        x=QLabel(text); x.setProperty('fieldLabel',True); return x
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(10)
        head=Card(); row=QHBoxLayout(); title=QLabel('ΠΡΟΣΤΙΜΑ'); title.setObjectName('Title'); row.addWidget(title); row.addStretch(1)
        self.preview_btn=QPushButton('ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΤΡΕΧΟΥΣΑΣ ΑΝΑΦΟΡΑΣ'); self.preview_btn.setObjectName('Primary'); self.preview_btn.clicked.connect(self.preview_report); row.addWidget(self.preview_btn)
        reports=QPushButton('ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ'); reports.clicked.connect(self.open_reports_archive); row.addWidget(reports)
        head.layout_box.addLayout(row); root.addWidget(head)
        form=Card()
        g=QGridLayout(); g.setHorizontalSpacing(14); g.setVerticalSpacing(8); form.layout_box.addLayout(g)
        self.kind=QComboBox(); self.kind.addItem('ΕΠΙΒΟΛΗ','IMPOSITION'); self.kind.addItem('ΕΙΣΠΡΑΞΗ','PAYMENT'); self.kind.currentIndexChanged.connect(self._sync_kind)
        self.date=QLineEdit(datetime.now().strftime('%d/%m/%Y')); self.imposition_protocol=QLineEdit(); self.paravolo=QLineEdit(); self.surname=QLineEdit(); self.name=QLineEdit(); self.birth_date=QLineEdit(); self.nationality=QLineEdit(); self.passport=QLineEdit(); self.measure=QLineEdit()
        self.amount=QComboBox(); self.amount.addItems(['600','1200']); self.collection_method=QComboBox(); self.collection_method.addItem(''); self.collection_method.addItems(list(COLLECTION_METHODS)); self.collection_method.setEditable(True); self.collection_protocol=QLineEdit(); self.responsible=QLineEdit()
        self.imposition_protocol.setPlaceholderText('π.χ. αριθμός πράξης επιβολής'); self.paravolo.setPlaceholderText('Αριθμός e-Παραβόλου, όπου υπάρχει'); self.birth_date.setPlaceholderText('ΗΗ/ΜΜ/ΕΕΕΕ'); self.responsible.setPlaceholderText('Αστυνομικός / αρμόδιος')
        fields=[('ΤΥΠΟΣ ΠΡΑΞΗΣ',self.kind),('ΗΜΕΡΟΜΗΝΙΑ',self.date),('ΑΡ. ΠΡΑΞΗΣ ΕΠΙΒΟΛΗΣ',self.imposition_protocol),('ΑΡΙΘΜΟΣ ΠΑΡΑΒΟΛΟΥ',self.paravolo),('ΕΠΩΝΥΜΟ',self.surname),('ΟΝΟΜΑ',self.name),('ΗΜ/ΝΙΑ ΓΕΝΝΗΣΗΣ',self.birth_date),('ΥΠΗΚΟΟΤΗΤΑ',self.nationality),('ΑΡ. ΔΙΑΒΑΤΗΡΙΟΥ',self.passport),('ΑΡ. ΜΕΤΡΟΥ',self.measure),('ΧΡΗΜΑΤΙΚΟ ΠΟΣΟ',self.amount),('ΤΡΟΠΟΣ ΕΙΣΠΡΑΞΗΣ',self.collection_method),('ΑΡ. ΠΡΩΤΟΚΟΛΛΟΥ ΕΙΣΠΡΑΞΗΣ',self.collection_protocol),('ΑΣΤΥΝΟΜΙΚΟΣ / ΑΡΜΟΔΙΟΣ',self.responsible)]
        for i,(lab,w) in enumerate(fields):
            side=0 if i<7 else 2; rr=i if i<7 else i-7; g.addWidget(self._label(lab),rr,side); g.addWidget(w,rr,side+1)
        g.setColumnStretch(1,1); g.setColumnStretch(3,1)
        self.edit_notice=QLabel(''); self.edit_notice.setWordWrap(True); self.edit_notice.hide(); form.layout_box.addWidget(self.edit_notice)
        actions=QHBoxLayout(); actions.addStretch(1); self.clear_btn=QPushButton('ΚΑΘΑΡΙΣΜΟΣ'); self.clear_btn.clicked.connect(self.clear_form); self.save_btn=QPushButton('ΚΑΤΑΧΩΡΙΣΗ'); self.save_btn.setObjectName('Primary'); self.save_btn.clicked.connect(self.save); actions.addWidget(self.clear_btn); actions.addWidget(self.save_btn); form.layout_box.addLayout(actions); root.addWidget(form)
        list_card=Card(); lr=QHBoxLayout(); lt=QLabel('ΤΡΕΧΟΥΣΑ ΒΑΡΔΙΑ — ΚΑΤΑΧΩΡΙΣΕΙΣ'); lt.setObjectName('SubTitle'); lr.addWidget(lt); lr.addStretch(1); archive=QPushButton('ΑΡΧΕΙΟ ΠΡΑΞΕΩΝ'); archive.clicked.connect(self.open_archive); lr.addWidget(archive); rb=QPushButton('ΑΝΑΝΕΩΣΗ'); rb.clicked.connect(self.refresh); lr.addWidget(rb); list_card.layout_box.addLayout(lr)
        self.edit_btn=QPushButton('ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ'); self.edit_btn.clicked.connect(self.edit_selected); lr.insertWidget(2,self.edit_btn)
        self.delete_btn=QPushButton('ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ'); self.delete_btn.clicked.connect(self.delete_selected); lr.insertWidget(3,self.delete_btn)
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(['Τύπος','Ημερομηνία','Επώνυμο','Όνομα','Ποσό','Πρωτόκολλο','Αστυνομικός / Αρμόδιος']); self.table.setAlternatingRowColors(True); self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.horizontalHeader().setStretchLastSection(True); list_card.layout_box.addWidget(self.table); root.addWidget(list_card,1); self._sync_kind()
        self.table.setSelectionMode(QTableWidget.SingleSelection); self.table.itemSelectionChanged.connect(self._sync_edit_button)
    def _sync_edit_button(self):
        enabled=self.table.currentRow()>=0 and self._editing_id is None
        self.edit_btn.setEnabled(enabled); self.delete_btn.setEnabled(enabled)

    def begin_edit(self, fine_id: int):
        row=self.service.get_fine(int(fine_id))
        if row is None: raise ValueError('Δεν βρέθηκε η επιλεγμένη πράξη.')
        entry=self.service._row_to_entry(row,for_report=False)
        self._editing_id=int(row['id']); self._editing_shift=int(row['shift_id']); self._original_entry=entry
        self.kind.setCurrentIndex(self.kind.findData(row['operation_type'])); self.kind.setEnabled(False)
        for name in ('date','imposition_protocol','paravolo','surname','name','birth_date','nationality','passport','measure','collection_protocol','responsible'):
            getattr(self,name).setText(getattr(entry,name))
        self.amount.setCurrentText(str(entry.amount)); self.collection_method.setCurrentText(entry.collection_method)
        self.save_btn.setText('ΑΠΟΘΗΚΕΥΣΗ ΔΙΟΡΘΩΣΗΣ'); self.save_btn.setEnabled(True); self.clear_btn.setText('ΑΚΥΡΩΣΗ ΔΙΟΡΘΩΣΗΣ')
        self.edit_notice.setText('Διορθώνετε την επιλεγμένη πράξη. Η αποθήκευση ενημερώνει την ίδια εγγραφή, τη συνδεδεμένη είσπραξη και όλες τις σχετικές αναφορές της βάρδιας.'); self.edit_notice.show()
        self._sync_edit_button(); self.surname.setFocus()

    def edit_selected(self):
        try:
            item=self.table.item(self.table.currentRow(),0)
            if item is None:return
            self.begin_edit(int(item.data(Qt.UserRole)))
        except Exception as exc: QMessageBox.warning(self,'Διόρθωση Προστίμου',str(exc))

    def delete_selected(self):
        try:
            item=self.table.item(self.table.currentRow(),0)
            if item is None: return
            row=self.service.get_fine(int(item.data(Qt.UserRole)))
            if row is None: raise ValueError('Δεν βρέθηκε η επιλεγμένη πράξη.')
            entry=self.service._row_to_entry(row,for_report=False)
            label='επιβολή' if row['operation_type']=='IMPOSITION' else 'είσπραξη'
            person=(f"{row['surname']} {row['given_name']}").strip()
            msg=f"Να διαγραφεί οριστικά η επιλεγμένη {label};\\n\\n{person} — {row['amount']} €\\n\\nΘα ενημερωθούν η συνδεδεμένη είσπραξη, οι αναφορές και η Ημερήσια Δραστηριότητα."
            if QMessageBox.question(self,'Επιβεβαίωση διαγραφής',msg,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            result=self.service.delete_fine(int(row['id']),expected_entry=entry)
            self.refresh()
            mw=self.window()
            if hasattr(mw,'pages'):
                for name in ('receipts','daily','reports'):
                    page=mw.pages.get(name)
                    if page is not None: page.refresh()
            if hasattr(mw,'refresh_pending'): mw.refresh_pending()
            if result.failed:
                from app.services.pending import PendingService
                details='\\n'.join(f'• {PendingService.label(t)}: {error}' for t,error in result.failed)
                QMessageBox.warning(self,'Η πράξη διαγράφηκε','Η πράξη διαγράφηκε από τα δεδομένα. Οι παρακάτω ενημερώσεις αρχείων έμειναν σε εκκρεμότητα:\\n\\n'+details)
            else: QMessageBox.information(self,'Ολοκληρώθηκε','Η πράξη διαγράφηκε και οι συνδεδεμένες εγγραφές ενημερώθηκαν.')
        except Exception as exc: QMessageBox.warning(self,'Διαγραφή Προστίμου',str(exc))

    def apply_person(self,x):
        self.surname.setText(x.get("surname",""))
        self.name.setText(x.get("given_name",""))
        self.birth_date.setText(x.get("birth_date",""))
        self.passport.setText(x.get("passport_no",""))
        self.nationality.setFocus()

    def _refresh_autocomplete(self):
        for widget,key in (
            (self.surname,"surname"),(self.name,"given_name"),(self.nationality,"nationality"),
            (self.passport,"passport"),(self.measure,"measure"),(self.responsible,"responsible"),
            (self.paravolo,"paravolo"),
        ):
            install_history_completer(widget,self.service.db.autocomplete_values(key))

    def _sync_kind(self):
        payment=self.kind.currentData()=='PAYMENT'
        for w in (self.collection_method,self.collection_protocol,self.paravolo): w.setEnabled(payment)
        self.responsible.setEnabled(True)
        self.imposition_protocol.setEnabled(not payment)
        if not payment:
            self.collection_method.setCurrentText(''); self.collection_protocol.clear(); self.paravolo.clear()
    def _entry(self):
        return FineEntry(date=self.date.text().strip(),imposition_protocol=self.imposition_protocol.text().strip(),paravolo=self.paravolo.text().strip(),surname=self.surname.text().strip(),name=self.name.text().strip(),birth_date=self.birth_date.text().strip(),nationality=self.nationality.text().strip(),passport=self.passport.text().strip(),measure=self.measure.text().strip(),amount=int(self.amount.currentText()),collection_method=self.collection_method.currentText().strip(),collection_protocol=self.collection_protocol.text().strip(),responsible=self.responsible.text().strip())
    def save(self):
        try:
            kind=self.kind.currentData(); label='Επιβολή' if kind=='IMPOSITION' else 'Είσπραξη'
            if self._editing_id is not None:
                if QMessageBox.question(self,'Επιβεβαίωση','Να αποθηκευτεί η διόρθωση της επιλεγμένης πράξης;',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
                result=self.service.update_fine(self._editing_id,self._entry(),expected_entry=self._original_entry)
                self.clear_form(keep_kind=True); self.refresh()
                mw=self.window()
                if hasattr(mw,'pages'):
                    for name in ('receipts','daily','reports'):
                        page=mw.pages.get(name)
                        if page is not None: page.refresh()
                if hasattr(mw,'refresh_pending'): mw.refresh_pending()
                if result.failed:
                    from app.services.pending import PendingService
                    details='\n'.join(f'• {PendingService.label(t)}: {error}' for t,error in result.failed)
                    QMessageBox.warning(self,'Η διόρθωση αποθηκεύτηκε','Τα δεδομένα διορθώθηκαν. Οι παρακάτω ενημερώσεις αρχείων έμειναν σε εκκρεμότητα:\n\n'+details)
                else: QMessageBox.information(self,'Ολοκληρώθηκε','Η διόρθωση αποθηκεύτηκε και οι συνδεδεμένες εγγραφές ενημερώθηκαν.')
                return
            if QMessageBox.question(self,'Επιβεβαίωση',f'Να καταχωριστεί η πράξη: {label};',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            self.service.add_fine(kind,self._entry()); self.refresh(); self.clear_form(keep_kind=True); QMessageBox.information(self,'Ολοκληρώθηκε','Η καταχώριση ολοκληρώθηκε.')
        except Exception as exc: QMessageBox.warning(self,'Η καταχώριση δεν ολοκληρώθηκε',str(exc))
    def clear_form(self,checked=False,keep_kind=False):
        self._editing_id=None; self._editing_shift=None; self._original_entry=None; self.kind.setEnabled(True)
        self.save_btn.setText('ΚΑΤΑΧΩΡΙΣΗ'); self.clear_btn.setText('ΚΑΘΑΡΙΣΜΟΣ'); self.edit_notice.hide()
        if not keep_kind:self.kind.setCurrentIndex(0)
        self.date.setText(datetime.now().strftime('%d/%m/%Y'))
        for w in (self.imposition_protocol,self.paravolo,self.surname,self.name,self.birth_date,self.nationality,self.passport,self.measure,self.collection_protocol,self.responsible):w.clear()
        self.amount.setCurrentText('600'); self.collection_method.setCurrentText(''); self._sync_kind(); self.surname.setFocus()
        self.save_btn.setEnabled(bool(self.service.db.get_open_shift())); self._sync_edit_button()
    def refresh(self):
        shift=self.service.db.get_current_or_last_shift(); rows=self.service.fines_for_shift(int(shift['id'])) if shift else []
        self.save_btn.setEnabled(self._editing_id is not None or bool(shift and shift['status']=='OPEN')); self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=['ΕΠΙΒΟΛΗ' if row['operation_type']=='IMPOSITION' else 'ΕΙΣΠΡΑΞΗ',row['fine_date'],row['surname'],row['given_name'],str(row['amount']),row['imposition_protocol'] if row['operation_type']=='IMPOSITION' else row['collection_protocol'],row['responsible'] or '']
            for c,v in enumerate(vals):
                item=QTableWidgetItem(v or ''); item.setFlags(item.flags() & ~Qt.ItemIsEditable); item.setData(Qt.UserRole,int(row['id'])); self.table.setItem(r,c,item)
        self.table.resizeColumnsToContents()
        report_shift=self.service.db.get_current_or_last_shift()
        report_rows=self.service.fines_for_shift(int(report_shift['id'])) if report_shift else []
        self.preview_btn.setEnabled(bool(report_shift and report_rows)); self._refresh_autocomplete()
        self._sync_edit_button()
    def open_reports_archive(self):
        mw=self.window()
        if hasattr(mw,'show_reports'):
            mw.show_reports('FINES')

    def open_archive(self): FinesArchiveDialog(self.service,self).exec()
    def preview_report(self):
        try:
            shift=self.service.db.get_current_or_last_shift()
            if not shift: raise ValueError('Δεν υπάρχει διαθέσιμη βάρδια για αναφορά.')
            path=self.service.generate_shift_report(int(shift['id']),archive=False)
            if path is None: raise ValueError('Δεν υπάρχουν καταχωρίσεις Προστίμων στη βάρδια.')
            if os.name=='nt': open_document_preview(path)
            else: QMessageBox.information(self,'Προεπισκόπηση',f'Δημιουργήθηκε:\n{path}')
        except Exception as exc: QMessageBox.warning(self,'Προεπισκόπηση Προστίμων',str(exc))
