from __future__ import annotations
from app.contracts import PageActions
import os
from app.infrastructure.pdf_preview import open_document_preview
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox,QFormLayout,QFrame,QGridLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QScrollArea,QSizePolicy,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from app.features.refusals.languages import LANGUAGES
from app.features.refusals.documents import REFUSAL_REASONS,RefusalEntry
from app.features.refusals.service import RefusalService
from app.features.refusals.archive import RefusalsArchiveDialog
from app.ui.widgets import Card
from app.features.people.autocomplete import install_history_completer

class RefusalsPage(QWidget):
    actions = PageActions()
    def __init__(self,service:RefusalService,parent=None): super().__init__(parent); self.service=service; self._editing_id=None; self._editing_shift=None; self._original_entry=None; self._build(); self.refresh()
    def _label(self,text): x=QLabel(text); x.setProperty('fieldLabel',True); return x
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(10)
        head=Card(); r=QHBoxLayout(); t=QLabel('ΑΡΝΗΣΕΙΣ'); t.setObjectName('Title'); r.addWidget(t); r.addStretch(1)
        head.layout_box.addLayout(r)
        tools=QHBoxLayout(); a=QPushButton('ΑΡΧΕΙΟ ΑΡΝΗΣΕΩΝ'); a.clicked.connect(self.open_archive); tools.addWidget(a); self.preview_btn=QPushButton('ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΤΡΕΧΟΥΣΑΣ ΑΡΝΗΣΗΣ'); self.preview_btn.clicked.connect(self.preview_latest); tools.addWidget(self.preview_btn); self.vas_btn=QPushButton('ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΒΑΣ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ'); self.vas_btn.setObjectName('Primary'); self.vas_btn.clicked.connect(self.preview_vas); tools.addWidget(self.vas_btn); reports=QPushButton('ΑΡΧΕΙΟ ΒΑΣ'); reports.clicked.connect(self.open_reports_archive); tools.addWidget(reports); tools.addStretch(1); head.layout_box.addLayout(tools); root.addWidget(head)
        self.f={}
        def line(k,default=''): w=QLineEdit(default); w.setProperty('dataField',True); self.f[k]=w; return w
        def combo(k,items,default=None): w=QComboBox(); w.addItems(items); w.setProperty('dataField',True); w.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon); w.setMinimumContentsLength(1); w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed); self.f[k]=w; (w.setCurrentText(default) if default else None); return w
        now=datetime.now()

        act_fields=[
            ('Α/Α ΠΡΑΞΗΣ',line('aa')),('ΕΤΟΣ Α/Α',line('year',str(now.year))),
            ('ΠΡΩΤΟΚΟΛΛΟ',line('protocol_prefix')),('ΑΡ. ΠΡΩΤΟΚΟΛΛΟΥ',line('protocol_no')),
            ('ΗΜΕΡΟΜΗΝΙΑ',line('date',now.strftime('%d-%m-%Y'))),('ΩΡΑ',line('time',now.strftime('%H:%M'))),
            ('ΛΟΓΟΣ ΑΡΝΗΣΗΣ',combo('reason',list(REFUSAL_REASONS))),
            ('ΓΛΩΣΣΑ ΕΓΓΡΑΦΟΥ',combo('language',list(LANGUAGES),'ΑΛΒΑΝΙΚΑ')),
        ]
        identity_fields=[
            ('ΦΥΛΟ',line('sex','M')),('ΕΠΩΝΥΜΟ',line('surname')),('ΟΝΟΜΑ',line('name')),
            ('ΗΜ/ΝΙΑ ΓΕΝΝΗΣΗΣ',line('birth_date')),('ΤΟΠΟΣ ΓΕΝΝΗΣΗΣ',line('birth_place','ΑΛΒΑΝΙΑ')),
            ('ΥΠΗΚΟΟΤΗΤΑ',line('nationality','ΑΛΒΑΝΙΚΗ')),('ΚΑΤΟΙΚΙΑ',line('residence')),
            ('ΑΡ. ΔΙΑΒΑΤΗΡΙΟΥ',line('passport')),('ΕΚΔΟΥΣΑ ΑΡΧΗ ΔΙΑΒΑΤΗΡΙΟΥ',line('passport_issuer','ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ')),
            ('ΗΜ/ΝΙΑ ΕΚΔΟΣΗΣ',line('issue_date')),('ΠΡΟΕΡΧΟΜΕΝΟΣ/Η ΑΠΟ',line('origin_country','ΑΛΒΑΝΙΑ (ALBANIA)')),
        ]
        measure_fields=[
            ('ΑΡΧΗ ΕΘΝ. ΜΕΤΡΟΥ',line('measure_country')),('ΑΡΙΘΜΟΣ ΜΕΤΡΟΥ',line('measure_no')),
            ('ΕΝΑΡΞΗ ΜΕΤΡΟΥ',line('measure_from')),('ΛΗΞΗ ΜΕΤΡΟΥ',line('measure_to')),
            ('ΑΡΧΗ SIS',line('sis_country')),('ΑΡΙΘΜΟΣ SIS',line('sis_no')),
            ('ΕΝΑΡΞΗ SIS',line('sis_from')),('ΛΗΞΗ SIS',line('sis_to')),
        ]
        self.f['aa'].setPlaceholderText('Α/Α πρώτης σελίδας')
        self.f['protocol_prefix'].setPlaceholderText('Πρόθεμα/σειρά πρωτοκόλλου')
        self.f['protocol_no'].setPlaceholderText('Αριθμός πρωτοκόλλου')
        self.f['birth_date'].setPlaceholderText('ΗΗ-ΜΜ-ΕΕΕΕ')

        def field_cell(label_text, widget):
            cell=QWidget(); box=QVBoxLayout(cell); box.setContentsMargins(0,0,0,0); box.setSpacing(3)
            box.addWidget(self._label(label_text)); box.addWidget(widget)
            return cell

        forms=QHBoxLayout(); forms.setSpacing(12)

        action_section=Card(); h=QLabel('ΠΡΑΞΗ'); h.setObjectName('SubTitle'); action_section.layout_box.addWidget(h)
        action_form=QFormLayout(); action_form.setVerticalSpacing(7); action_form.setLabelAlignment(Qt.AlignLeft)
        action_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        for lab,w in act_fields:
            action_form.addRow(self._label(lab),w)
        action_section.layout_box.addLayout(action_form)
        forms.addWidget(action_section,3)

        identity_section=Card(); h=QLabel('ΣΤΟΙΧΕΙΑ ΠΡΟΣΩΠΟΥ'); h.setObjectName('SubTitle'); identity_section.layout_box.addWidget(h)
        identity_grid=QGridLayout(); identity_grid.setHorizontalSpacing(12); identity_grid.setVerticalSpacing(7)
        identity_grid.setColumnStretch(0,1); identity_grid.setColumnStretch(1,1)
        identity_pairs=[
            (('ΦΥΛΟ',self.f['sex']),('ΕΠΩΝΥΜΟ',self.f['surname'])),
            (('ΟΝΟΜΑ',self.f['name']),('ΗΜ/ΝΙΑ ΓΕΝΝΗΣΗΣ',self.f['birth_date'])),
            (('ΤΟΠΟΣ ΓΕΝΝΗΣΗΣ',self.f['birth_place']),('ΥΠΗΚΟΟΤΗΤΑ',self.f['nationality'])),
            (('ΚΑΤΟΙΚΙΑ',self.f['residence']),('ΑΡ. ΔΙΑΒΑΤΗΡΙΟΥ',self.f['passport'])),
            (('ΗΜ/ΝΙΑ ΕΚΔΟΣΗΣ',self.f['issue_date']),('ΠΡΟΕΡΧΟΜΕΝΟΣ/Η ΑΠΟ',self.f['origin_country'])),
        ]
        for row,pair in enumerate(identity_pairs):
            for col,(lab,w) in enumerate(pair):
                identity_grid.addWidget(field_cell(lab,w),row,col)
        identity_grid.addWidget(field_cell('ΕΚΔΟΥΣΑ ΑΡΧΗ ΔΙΑΒΑΤΗΡΙΟΥ',self.f['passport_issuer']),len(identity_pairs),0,1,2)
        identity_section.layout_box.addLayout(identity_grid)
        forms.addWidget(identity_section,5)

        measure_section=Card(); h=QLabel('ΜΕΤΡΑ / SIS'); h.setObjectName('SubTitle'); measure_section.layout_box.addWidget(h)
        national_title=QLabel('ΕΘΝΙΚΟ ΜΕΤΡΟ'); national_title.setObjectName('SubTitle'); measure_section.layout_box.addWidget(national_title)
        national_grid=QGridLayout(); national_grid.setHorizontalSpacing(10); national_grid.setVerticalSpacing(7)
        national_grid.setColumnStretch(0,1); national_grid.setColumnStretch(1,1)
        national_grid.addWidget(field_cell('ΑΡΧΗ',self.f['measure_country']),0,0)
        national_grid.addWidget(field_cell('ΑΡΙΘΜΟΣ',self.f['measure_no']),0,1)
        national_grid.addWidget(field_cell('ΕΝΑΡΞΗ',self.f['measure_from']),1,0)
        national_grid.addWidget(field_cell('ΛΗΞΗ',self.f['measure_to']),1,1)
        measure_section.layout_box.addLayout(national_grid)
        sis_title=QLabel('SIS'); sis_title.setObjectName('SubTitle'); measure_section.layout_box.addWidget(sis_title)
        sis_grid=QGridLayout(); sis_grid.setHorizontalSpacing(10); sis_grid.setVerticalSpacing(7)
        sis_grid.setColumnStretch(0,1); sis_grid.setColumnStretch(1,1)
        sis_grid.addWidget(field_cell('ΑΡΧΗ',self.f['sis_country']),0,0)
        sis_grid.addWidget(field_cell('ΑΡΙΘΜΟΣ',self.f['sis_no']),0,1)
        sis_grid.addWidget(field_cell('ΕΝΑΡΞΗ',self.f['sis_from']),1,0)
        sis_grid.addWidget(field_cell('ΛΗΞΗ',self.f['sis_to']),1,1)
        measure_section.layout_box.addLayout(sis_grid)
        measure_section.layout_box.addStretch(1)
        forms.addWidget(measure_section,4)

        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page_body=QWidget(); body=QVBoxLayout(page_body); body.setContentsMargins(0,0,0,0); body.setSpacing(10)
        body.addLayout(forms)

        note=QLabel('Α/Α και Πρωτόκολλο είναι ξεχωριστά πεδία.'); note.setObjectName('SubTitle'); body.addWidget(note)
        ar=QHBoxLayout(); ar.addStretch(1)
        self.edit_notice=QLabel(''); self.edit_notice.setWordWrap(True); self.edit_notice.hide(); body.addWidget(self.edit_notice)
        self.clear_btn=QPushButton('ΚΑΘΑΡΙΣΜΟΣ'); self.clear_btn.setMaximumHeight(42); self.clear_btn.setMinimumWidth(110); self.clear_btn.clicked.connect(self.clear); self.save_btn=QPushButton('ΚΑΤΑΧΩΡΙΣΗ / ΔΗΜΙΟΥΡΓΙΑ'); self.save_btn.setMaximumHeight(42); self.save_btn.setMinimumWidth(190); self.save_btn.setObjectName('Primary'); self.save_btn.clicked.connect(self.save); ar.addWidget(self.clear_btn); ar.addWidget(self.save_btn); body.addLayout(ar)

        list_card=Card(); lr=QHBoxLayout(); lt=QLabel('ΑΡΝΗΣΕΙΣ ΒΑΡΔΙΑΣ — ΚΑΤΑΧΩΡΙΣΕΙΣ'); lt.setObjectName('SubTitle'); lr.addWidget(lt); lr.addStretch(1)
        self.edit_btn=QPushButton('ΔΙΟΡΘΩΣΗ ΕΠΙΛΕΓΜΕΝΗΣ'); self.edit_btn.clicked.connect(self.edit_selected); lr.addWidget(self.edit_btn)
        self.delete_btn=QPushButton('ΔΙΑΓΡΑΦΗ ΕΠΙΛΕΓΜΕΝΗΣ'); self.delete_btn.clicked.connect(self.delete_selected); lr.addWidget(self.delete_btn)
        rb=QPushButton('ΑΝΑΝΕΩΣΗ'); rb.clicked.connect(self.refresh); lr.addWidget(rb); list_card.layout_box.addLayout(lr)
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(['Ημερομηνία/ώρα','Επώνυμο','Όνομα','Διαβατήριο','Λόγος','Α/Α','Πρωτόκολλο']); self.table.setAlternatingRowColors(True); self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection); self.table.horizontalHeader().setStretchLastSection(True); self.table.setMinimumHeight(150); list_card.layout_box.addWidget(self.table); body.addWidget(list_card)
        body.addStretch(1); scroll.setWidget(page_body); root.addWidget(scroll,1)
        self.table.itemSelectionChanged.connect(self._sync_edit_button)
    def apply_person(self,x):
        self.f["surname"].setText(x.get("surname",""))
        self.f["name"].setText(x.get("given_name",""))
        self.f["birth_date"].setText(x.get("birth_date",""))
        self.f["passport"].setText(x.get("passport_no",""))
        self.f["issue_date"].setFocus()

    def _refresh_autocomplete(self):
        for key,source in (
            ("surname","surname"),("name","given_name"),("passport","passport"),
            ("birth_place","birth_place"),("nationality","nationality"),("residence","residence"),
            ("passport_issuer","passport_issuer"),("origin_country","origin_country"),
            ("measure_country","measure_country"),("measure_no","measure_no"),
            ("sis_country","sis_country"),("sis_no","sis_no"),
        ):
            install_history_completer(self.f[key],self.service.db.autocomplete_values(source))

    def _sync_edit_button(self):
        enabled=self.table.currentRow()>=0 and self._editing_id is None
        self.edit_btn.setEnabled(enabled); self.delete_btn.setEnabled(enabled)

    def begin_edit(self, refusal_id: int):
        row=self.service.get_refusal(int(refusal_id))
        if row is None: raise ValueError('Δεν βρέθηκε η επιλεγμένη άρνηση.')
        entry=self.service._row_to_entry(row)
        self._editing_id=int(row['id']); self._editing_shift=int(row['shift_id']); self._original_entry=entry
        for key in ('aa','year','protocol_prefix','protocol_no','date','time','sex','surname','name','birth_date','passport','issue_date','measure_country','measure_no','measure_from','measure_to','sis_country','sis_no','sis_from','sis_to','birth_place','nationality','residence','passport_issuer','origin_country'):
            self.f[key].setText(getattr(entry,key))
        self.f['reason'].setCurrentText(entry.reason); self.f['language'].setCurrentText(entry.language)
        self.save_btn.setText('ΑΠΟΘΗΚΕΥΣΗ ΔΙΟΡΘΩΣΗΣ'); self.save_btn.setEnabled(True); self.clear_btn.setText('ΑΚΥΡΩΣΗ ΔΙΟΡΘΩΣΗΣ')
        self.edit_notice.setText('Διορθώνετε την επιλεγμένη άρνηση. Η αποθήκευση ενημερώνει την ίδια εγγραφή, την ατομική άρνηση, το ΒΑΣ και την Ημερήσια Δραστηριότητα της αντίστοιχης βάρδιας.'); self.edit_notice.show()
        self._sync_edit_button(); self.f['surname'].setFocus()

    def edit_selected(self):
        try:
            item=self.table.item(self.table.currentRow(),0)
            if item is None:return
            self.begin_edit(int(item.data(Qt.UserRole)))
        except Exception as exc: QMessageBox.warning(self,'Διόρθωση Άρνησης',str(exc))

    def delete_selected(self):
        try:
            item=self.table.item(self.table.currentRow(),0)
            if item is None:return
            row=self.service.get_refusal(int(item.data(Qt.UserRole)))
            if row is None: raise ValueError('Δεν βρέθηκε η επιλεγμένη άρνηση.')
            entry=self.service._row_to_entry(row)
            person=(f"{row['surname']} {row['given_name']}").strip()
            msg=f"Να διαγραφεί οριστικά η επιλεγμένη άρνηση;\n\n{person} — {row['refusal_date']}\n\nΘα ενημερωθούν η ατομική άρνηση, το ΒΑΣ και η Ημερήσια Δραστηριότητα της βάρδιας."
            if QMessageBox.question(self,'Επιβεβαίωση διαγραφής',msg,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            result=self.service.delete_refusal(int(row['id']),expected_entry=entry)
            self.refresh(); self._refresh_related_pages()
            self._show_pending_result(result,'Η άρνηση διαγράφηκε','Η άρνηση διαγράφηκε από τα δεδομένα.')
        except Exception as exc: QMessageBox.warning(self,'Διαγραφή Άρνησης',str(exc))

    def _refresh_related_pages(self):
        self.actions.refresh_pages(('daily', 'reports'))
        self.actions.refresh_pending()

    def _show_pending_result(self,result,success_title,prefix):
        if result.failed:
            from app.features.reports.pending import PendingService
            details='\n'.join(f'• {PendingService.label(t)}: {error}' for t,error in result.failed)
            QMessageBox.warning(self,success_title,prefix+' Οι παρακάτω ενημερώσεις αρχείων έμειναν σε εκκρεμότητα:\n\n'+details)
        else:
            QMessageBox.information(self,'Ολοκληρώθηκε',prefix+' Όλα τα συνδεδεμένα αρχεία ενημερώθηκαν.')

    def v(self,k): w=self.f[k]; return w.currentText().strip() if isinstance(w,QComboBox) else w.text().strip()
    def entry(self): return RefusalEntry(**{k:self.v(k) for k in ('aa','year','protocol_prefix','protocol_no','date','time','sex','surname','name','birth_date','passport','issue_date','reason','measure_country','measure_no','measure_from','measure_to','sis_country','sis_no','sis_from','sis_to','language','birth_place','nationality','residence','passport_issuer','origin_country')})
    def save(self):
        try:
            e=self.entry(); e.validate()
            if self._editing_id is not None:
                if QMessageBox.question(self,'Επιβεβαίωση','Να αποθηκευτεί η διόρθωση της επιλεγμένης άρνησης;',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
                result=self.service.update_refusal(self._editing_id,e,expected_entry=self._original_entry)
                self.clear(); self.refresh(); self._refresh_related_pages()
                self._show_pending_result(result,'Η διόρθωση αποθηκεύτηκε','Τα δεδομένα της άρνησης διορθώθηκαν.')
                return
            if QMessageBox.question(self,'Επιβεβαίωση','Να καταχωριστεί και να δημιουργηθεί η άρνηση;',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            _,latest,_,_=self.service.add_refusal(e); self.refresh(); QMessageBox.information(self,'Ολοκληρώθηκε',f'Η άρνηση δημιουργήθηκε.\n\n{latest}')
        except Exception as exc: QMessageBox.warning(self,'Η άρνηση δεν ολοκληρώθηκε',str(exc))
    def clear(self,checked=False):
        self._editing_id=None; self._editing_shift=None; self._original_entry=None
        self.save_btn.setText('ΚΑΤΑΧΩΡΙΣΗ / ΔΗΜΙΟΥΡΓΙΑ'); self.clear_btn.setText('ΚΑΘΑΡΙΣΜΟΣ'); self.edit_notice.hide()
        now=datetime.now()
        for w in self.f.values():
            if not isinstance(w,QComboBox): w.clear()
        self.f['year'].setText(str(now.year)); self.f['date'].setText(now.strftime('%d-%m-%Y')); self.f['time'].setText(now.strftime('%H:%M')); self.f['sex'].setText('M'); self.f['language'].setCurrentText('ΑΛΒΑΝΙΚΑ'); self.f['birth_place'].setText('ΑΛΒΑΝΙΑ'); self.f['nationality'].setText('ΑΛΒΑΝΙΚΗ'); self.f['passport_issuer'].setText('ΑΛΒΑΝΙΚΕΣ ΑΡΧΕΣ'); self.f['origin_country'].setText('ΑΛΒΑΝΙΑ (ALBANIA)'); self.f['surname'].setFocus()
        self.save_btn.setEnabled(bool(self.service.db.get_open_shift())); self._sync_edit_button()
    def refresh(self):
        open_shift=self.service.db.get_open_shift()
        shift=self.service.db.get_current_or_last_shift(); rows=self.service.refusals_for_shift(int(shift['id'])) if shift else []
        self.save_btn.setEnabled(self._editing_id is not None or bool(open_shift)); self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[(row['occurred_at'] or '').replace('T',' '),row['surname'] or '',row['given_name'] or '',row['passport_no'] or '',row['reason'] or '',f"{row['aa']}/{row['refusal_year']}",f"{row['protocol_prefix']}/{row['protocol_no']}"]
            for col,value in enumerate(vals):
                item=QTableWidgetItem(value); item.setFlags(item.flags() & ~Qt.ItemIsEditable); item.setData(Qt.UserRole,int(row['id'])); self.table.setItem(r,col,item)
        self.table.resizeColumnsToContents()
        visible_rows=max(4,min(len(rows),10)); desired=self.table.horizontalHeader().sizeHint().height()+visible_rows*self.table.verticalHeader().defaultSectionSize()+10
        self.table.setFixedHeight(max(150,desired))
        self.vas_btn.setEnabled(bool(shift and rows)); self.preview_btn.setEnabled(self.service.latest_refusal_path().exists()); self._refresh_autocomplete(); self._sync_edit_button()

    def open_reports_archive(self):
        self.actions.show_reports('VAS')

    def open_archive(self): RefusalsArchiveDialog(self.service,self).exec()
    def preview_latest(self):
        p=self.service.latest_refusal_path()
        if not p.exists(): QMessageBox.information(self,'Αρνήσεις','Δεν υπάρχει ακόμη τελευταία άρνηση.'); return
        if os.name=='nt': open_document_preview(p)
        else: QMessageBox.information(self,'Προεπισκόπηση',str(p))
    def preview_vas(self):
        try:
            shift=self.service.db.get_current_or_last_shift()
            if not shift: raise ValueError('Δεν υπάρχει διαθέσιμη βάρδια για ΒΑΣ.')
            p=self.service.generate_vas(int(shift['id']),archive=False)
            if not p: raise ValueError('Δεν υπάρχουν αρνήσεις στη βάρδια.')
            if os.name=='nt': open_document_preview(p)
            else: QMessageBox.information(self,'Προεπισκόπηση ΒΑΣ',str(p))
        except Exception as exc: QMessageBox.warning(self,'ΒΑΣ',str(exc))
