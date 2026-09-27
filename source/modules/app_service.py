from __future__ import annotations
import json, os, shutil, time, platform, uuid
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, date, timedelta
from pathlib import Path

from .app_config import AppConfig, app_dir
from .common import operational_date, GREEK_MONTHS, clean
from .fines_engine import FineEntry, FineReportEngine
from .refusals_engine import RefusalEntry, RefusalDocumentEngine, VasReportEngine
from .periodicals_engine import Package, PackageFile, PeriodicalsEngine, PreparationResult, IncompletePackageError
from .state_store import StateStore
from .fine_protocol import (
    receipt_from_fine, protocol_totals, summary_row, protocol_bucket_from_responsible, protocol_filename_key,
    ExcelComProtocolAdapter, MemoryProtocolAdapter,
)
from .activity_engine import (
    ActivityPlan, ActivityResult, ExcelComActivityAdapter,
    fine_activity_plan, refusal_activity_plan,
)


def resource_path(name:str)->Path:
    import sys
    base=Path(getattr(sys,'_MEIPASS',app_dir()))
    p=base/'resources'/name
    return p if p.exists() else app_dir()/'resources'/name

@contextmanager
def exclusive_lock(path:Path, retries:int=10, delay:float=2.0):
    path.parent.mkdir(parents=True,exist_ok=True); fd=None
    for _ in range(retries+1):
        try:
            fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            os.write(fd,f'pid={os.getpid()} time={datetime.now().isoformat()}'.encode('utf-8'))
            break
        except FileExistsError:
            time.sleep(delay)
    if fd is None: raise TimeoutError('Η καταχώριση χρησιμοποιείται προσωρινά από άλλον σταθμό.')
    try: yield
    finally:
        try: os.close(fd)
        except Exception: pass
        try: path.unlink(missing_ok=True)
        except Exception: pass


class ProtocolDecisionRequired(RuntimeError):
    def __init__(self, responsible: str, workbook: Path):
        self.responsible = responsible
        self.workbook = Path(workbook)
        super().__init__(f"Υπάρχει ήδη Πρωτόκολλο για {responsible}. Επιλέξτε Συνέχιση ή Δημιουργία νέου.")


class AutonomousService:
    """Headless orchestration layer. No VBA is invoked at runtime."""
    def __init__(self,cfg:AppConfig, activity_adapter=None, protocol_adapter=None):
        self.cfg=cfg
        root=Path(cfg.data_root) if clean(cfg.data_root) else app_dir()/'TDE_DATA'
        root.mkdir(parents=True,exist_ok=True);self.root=root
        self.store=StateStore(root)
        self.fines_dir=root/'ΠΡΟΣΤΙΜΑ';self.refusal_dir=root/'ΑΡΝΗΣΕΙΣ';self.periodicals_dir=root/'ΠΕΡΙΟΔΙΚΑ'
        for p in (self.fines_dir,self.refusal_dir,self.periodicals_dir):p.mkdir(parents=True,exist_ok=True)
        self._activity_adapter = activity_adapter
        self._protocol_adapter = protocol_adapter
        self._protocol_session_decisions: set[str] = set()
        self.last_activity_result = ActivityResult(applied=False)

    # -------------------- ΠΡΟΣΤΙΜΑ --------------------
    def _fines_runtime_path(self) -> Path:
        return self.fines_dir / 'fines_runtime.json'

    def _load_fines_runtime(self) -> dict:
        p = self._fines_runtime_path()
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_fines_runtime(self, data: dict) -> None:
        p = self._fines_runtime_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, p)

    def fine_live_report(self, when:datetime|None=None)->Path:
        # One live Anafora.docx, exactly as in the VBA workflow. New-report creation is
        # now an explicit operator decision rather than manual clearing.
        return self.fines_dir/'Anafora.docx'

    def fine_report_prompt_needed(self, when: datetime | None = None) -> bool:
        """Ask once after the 10:00 boundary, or whenever no live report exists."""
        when = when or datetime.now()
        if not self.fine_live_report(when).exists():
            return True
        if when.hour < 10:
            return False
        rt = self._load_fines_runtime()
        return rt.get('report_prompt_day') != when.date().isoformat()

    def mark_fine_report_prompted(self, when: datetime | None = None) -> None:
        when = when or datetime.now()
        rt = self._load_fines_runtime()
        rt['report_prompt_day'] = when.date().isoformat()
        self._save_fines_runtime(rt)

    def current_fine_report_window(self) -> tuple[datetime | None, datetime | None]:
        rt = self._load_fines_runtime()
        def parse(key):
            try: return datetime.fromisoformat(str(rt.get(key, '')))
            except Exception: return None
        return parse('report_start'), parse('report_end')

    def _archive_live_fine_report(self) -> Path | None:
        src = self.fine_live_report()
        if not src.exists():
            return None
        start_dt, end_dt = self.current_fine_report_window()
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if start_dt and end_dt:
            label = f"{start_dt:%Y%m%d_%H%M}-{end_dt:%Y%m%d_%H%M}"
        else:
            label = stamp
        folder = self.fines_dir / 'ΑΡΧΕΙΟ ΠΡΟΗΓΟΥΜΕΝΩΝ ΑΝΑΦΟΡΩΝ'
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f'Anafora_{label}.docx'
        n = 2
        while dest.exists():
            dest = folder / f'Anafora_{label}_{n}.docx'; n += 1
        shutil.copy2(src, dest)
        return dest

    def create_new_fine_report(self, start_dt: datetime, end_dt: datetime) -> Path:
        """Archive the current live report and atomically replace it with a clean one."""
        if end_dt <= start_dt:
            raise ValueError('Η λήξη της αναφοράς πρέπει να είναι μετά την έναρξη.')
        p = self.fine_live_report()
        with exclusive_lock(self.fines_dir/'script_lock.tmp', retries=10, delay=2.0):
            if p.exists():
                self._archive_live_fine_report()
            tmp = p.with_suffix('.docx.new')
            try:
                FineReportEngine(resource_path('Anafora_base.docx')).create_report_window(
                    tmp, officer_name=self.cfg.officer_name, officer_agms=self.cfg.officer_agms,
                    start_dt=start_dt, end_dt=end_dt, officer_rank_short=self.cfg.officer_rank_short,
                    officer_rank_full=self.cfg.officer_rank_full,
                )
                os.replace(tmp, p)
            finally:
                tmp.unlink(missing_ok=True)
        rt = self._load_fines_runtime()
        rt['report_start'] = start_dt.isoformat(timespec='minutes')
        rt['report_end'] = end_dt.isoformat(timespec='minutes')
        rt['report_prompt_day'] = datetime.now().date().isoformat()
        self._save_fines_runtime(rt)
        return p

    def ensure_fine_report(self,when:datetime|None=None)->Path:
        # Safety fallback for headless/service calls. The GUI normally asks the user
        # before this path is needed.
        when=when or datetime.now();op=operational_date(when);p=self.fine_live_report(when)
        if not p.exists():
            FineReportEngine(resource_path('Anafora_base.docx')).create_report(
                p,officer_name=self.cfg.officer_name,officer_agms=self.cfg.officer_agms,
                operational_day=op,officer_rank_short=self.cfg.officer_rank_short,officer_rank_full=self.cfg.officer_rank_full)
            rt=self._load_fines_runtime(); start=datetime.combine(op, datetime.min.time()).replace(hour=10); end=start+timedelta(days=1)
            rt['report_start']=start.isoformat(timespec='minutes');rt['report_end']=end.isoformat(timespec='minutes')
            self._save_fines_runtime(rt)
        return p

    def _officer_key(self)->str:
        return (clean(self.cfg.officer_agms) or clean(self.cfg.officer_name) or 'AXYP').upper()

    def fine_protocol_workbook(self, responsible: str = '')->Path:
        folder = self.fines_dir / 'ΠΡΩΤΟΚΟΛΛΑ'
        folder.mkdir(parents=True, exist_ok=True)
        key = protocol_filename_key(responsible)
        return folder / f'ΠΡΩΤΟΚΟΛΛΟ - {key}.xlsx'

    def _protocol_owner_key(self, responsible: str) -> str:
        return protocol_bucket_from_responsible(responsible)

    def _protocol_instance_id(self, responsible: str, *, create: bool = True) -> str:
        owner = self._protocol_owner_key(responsible)
        rt = self._load_fines_runtime()
        items = rt.setdefault('protocol_instances', {})
        val = clean(items.get(owner, ''))
        if not val and create:
            val = f"{owner}#{uuid.uuid4().hex[:12].upper()}"
            items[owner] = val
            self._save_fines_runtime(rt)
        return val

    def protocol_decision_needed(self, responsible: str) -> bool:
        owner = self._protocol_owner_key(responsible)
        return self.fine_protocol_workbook(responsible).exists() and owner not in self._protocol_session_decisions

    def select_protocol_mode(self, responsible: str, *, create_new: bool) -> Path:
        """Resolve NEW/CONTINUE once per responsible person for the current app run."""
        owner = self._protocol_owner_key(responsible)
        p = self.fine_protocol_workbook(responsible)
        if create_new and p.exists():
            archive = p.parent / 'ΑΡΧΕΙΟ' / protocol_filename_key(responsible)
            archive.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dest = archive / f'{p.stem}_{stamp}{p.suffix}'
            n = 2
            while dest.exists():
                dest = archive / f'{p.stem}_{stamp}_{n}{p.suffix}'; n += 1
            shutil.move(str(p), str(dest))
            if hasattr(self._protocol_writer(), 'reset'):
                try: self._protocol_writer().reset(p)
                except Exception: pass
            rt = self._load_fines_runtime()
            rt.setdefault('protocol_instances', {})[owner] = f"{owner}#{uuid.uuid4().hex[:12].upper()}"
            self._save_fines_runtime(rt)
        else:
            self._protocol_instance_id(responsible, create=True)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resource_path('Fine_Protocol_Base.xlsx'), p)
        self._protocol_session_decisions.add(owner)
        return p

    def _protocol_writer(self):
        if self._protocol_adapter is None:
            if platform.system().lower() == 'windows':
                self._protocol_adapter=ExcelComProtocolAdapter(resource_path('Fine_Protocol_Base.xlsx'))
            else:
                # Deterministic simulation path. Production Windows uses Excel COM.
                self._protocol_adapter=MemoryProtocolAdapter()
        return self._protocol_adapter

    def add_fine(self,e:FineEntry,when:datetime|None=None,receipt_sequence:str="")->Path:
        e.validate(); when=when or datetime.now(); op=operational_date(when)
        # Preflight the new per-responsible protocol decision before touching Word/DB,
        # so cancelling NEW/CONTINUE can never leave a partial payment transaction.
        if not e.is_imposition and not clean(receipt_sequence):
            owner=self._protocol_owner_key(e.responsible)
            protocol_path=self.fine_protocol_workbook(e.responsible)
            if protocol_path.exists() and owner not in self._protocol_session_decisions:
                raise ProtocolDecisionRequired(owner,protocol_path)
            if not protocol_path.exists():
                # New surname: create its clean protocol automatically before the main
                # transaction, exactly as approved. No NEW/CONTINUE question is needed.
                self.select_protocol_mode(e.responsible,create_new=False)
        report=self.ensure_fine_report(when)
        allocated_receipt=""
        with exclusive_lock(self.fines_dir/'script_lock.tmp',retries=10,delay=2.0):
            # Exact VBA order: retry old Daily Activity items before the new main transaction.
            self.retry_pending_activity(10)
            FineReportEngine(resource_path('Anafora_base.docx')).write_entries(report,[e],source_docx=report)
            fine_id=self.store.add_fine(e, op)
            if not e.is_imposition:
                owner = self._protocol_owner_key(e.responsible)
                protocol_path = self.fine_protocol_workbook(e.responsible)
                if clean(receipt_sequence):
                    # Compatibility hook used only by deterministic simulations.
                    allocated_receipt=clean(receipt_sequence)
                    receipt=receipt_from_fine(e,int(allocated_receipt),officer_key=self._officer_key(),op_date=op.isoformat())
                else:
                    receipt=self._protocol_writer().append(protocol_path,e)
                    allocated_receipt=str(receipt.sequence)
                instance = self._protocol_instance_id(e.responsible, create=True)
                receipt = replace(receipt, protocol_bucket=instance)
                self.store.record_protocol_receipt(fine_id=fine_id,receipt=receipt)
        # Daily Activity is secondary. Unknown collection method in the VBA is a
        # warning after Word/Protocol have already been committed; it is not rollback.
        try:
            plan=fine_activity_plan(e,allocated_receipt)
        except Exception as exc:
            self.last_activity_result=ActivityResult(applied=False,error=str(exc))
            return report
        self.last_activity_result=self._apply_activity(plan,retry_pending=False)
        return report

    def fine_protocol_receipts(self, responsible: str = ""):
        instance = self._protocol_instance_id(responsible, create=False)
        return self.store.protocol_receipts(instance) if instance else []

    def fine_protocol_summary(self, responsible: str = "")->dict:
        instance=self._protocol_instance_id(responsible, create=False)
        rows=self.store.protocol_receipts(instance) if instance else []
        out=protocol_totals(rows)
        out['count']=len(rows); out['summary_row']=summary_row(len(rows)); out['protocol_bucket']=instance
        return out

    def fine_archive_target(self,when:datetime|None=None)->Path:
        """Exact date/folder naming of supplied postima.bat (month is zero-padded there)."""
        when=when or datetime.now();today=when.date()
        if when.hour<10: op=today-timedelta(days=1);rep=today
        else: op=today;rep=today+timedelta(days=1)
        base=Path(self.cfg.fines_archive_root) if clean(self.cfg.fines_archive_root) else self.fines_dir/'ΑΡΧΕΙΟ'
        dest=base/str(rep.year)/f'{rep.month:02d}. {GREEK_MONTHS[rep.month]} {rep.year}'/rep.strftime('%d-%m-%Y')
        name=f'Αναφορά για Επιβολή - Είσπραξη Προστίμων {op.day}-{rep.day}.{rep.month}.{rep.year}.docx'
        return dest/name

    def archive_fine_report(self,when:datetime|None=None)->Path:
        src=self.ensure_fine_report(when);dest=self.fine_archive_target(when);dest.parent.mkdir(parents=True,exist_ok=True)
        # Supplied BAT explicitly does not replace an existing report.
        if not dest.exists():shutil.copy2(src,dest)
        return dest

    # -------------------- ΑΡΝΗΣΕΙΣ --------------------
    def _refusals_runtime_path(self) -> Path:
        return self.refusal_dir / 'refusals_runtime.json'

    def _load_refusals_runtime(self) -> dict:
        p = self._refusals_runtime_path()
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_refusals_runtime(self, data: dict) -> None:
        p = self._refusals_runtime_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, p)

    def refusal_output(self)->Path:
        p=self.refusal_dir/'2_ΤΡΕΧΟΥΣΕΣ_ΕΚΤΥΠΩΣΕΙΣ';p.mkdir(parents=True,exist_ok=True);return p/'ΕΝΕΡΓΗ_ΑΡΝΗΣΗ_ΕΚΤΥΠΩΣΗ.docx'

    def vas_report(self,op:date|None=None)->Path:
        # One live ΒΑΣ_ΣΗΜΕΡΙΝΟ, matching the VBA filename/workflow.
        return self.refusal_dir/'ΒΑΣ_ΣΗΜΕΡΙΝΟ.docx'

    def _refusals_for_date(self,op:date)->list[RefusalEntry]:
        return self.store.refusals_for_date(op)

    def vas_prompt_needed(self, when: datetime | None = None) -> bool:
        """Ask once after 10:00, or whenever no live VAS exists.

        10:00 is only a reminder boundary.  The operator can define any actual
        start/end date and time for the new VAS.
        """
        when = when or datetime.now()
        if not self.vas_report().exists():
            return True
        if when.hour < 10:
            return False
        rt = self._load_refusals_runtime()
        return rt.get('vas_prompt_day') != when.date().isoformat()

    def mark_vas_prompted(self, when: datetime | None = None) -> None:
        when = when or datetime.now()
        rt = self._load_refusals_runtime()
        rt['vas_prompt_day'] = when.date().isoformat()
        self._save_refusals_runtime(rt)

    def current_vas_window(self) -> tuple[datetime | None, datetime | None]:
        rt = self._load_refusals_runtime()
        def parse(key):
            try: return datetime.fromisoformat(str(rt.get(key, '')))
            except Exception: return None
        return parse('vas_start'), parse('vas_end')

    def _archive_live_vas(self) -> Path | None:
        src = self.vas_report()
        if not src.exists():
            return None
        start_dt, end_dt = self.current_vas_window()
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        label = f"{start_dt:%Y%m%d_%H%M}-{end_dt:%Y%m%d_%H%M}" if start_dt and end_dt else stamp
        folder = self.refusal_dir / 'ΑΡΧΕΙΟ ΠΡΟΗΓΟΥΜΕΝΩΝ ΒΑΣ'
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f'ΒΑΣ_{label}.docx'
        n = 2
        while dest.exists():
            dest = folder / f'ΒΑΣ_{label}_{n}.docx'; n += 1
        shutil.copy2(src, dest)
        return dest

    def create_new_vas(self, start_dt: datetime, end_dt: datetime) -> Path:
        """Archive the active VAS and create a clean one for an operator-defined shift."""
        if end_dt <= start_dt:
            raise ValueError('Η λήξη του ΒΑΣ πρέπει να είναι μετά την έναρξη.')
        p = self.vas_report()
        with exclusive_lock(self.refusal_dir/'script_lock.tmp', retries=10, delay=0.25):
            if p.exists():
                self._archive_live_vas()
            tmp = p.with_suffix('.docx.new')
            try:
                VasReportEngine(resource_path('VAS_base.docx')).create(
                    tmp, [], start_dt.strftime('%d-%m-%Y'), end_dt.strftime('%d-%m-%Y'),
                    start_time=start_dt.strftime('%H:%M'), end_time=end_dt.strftime('%H:%M')
                )
                os.replace(tmp, p)
            finally:
                tmp.unlink(missing_ok=True)
        rt = self._load_refusals_runtime()
        rt['vas_start'] = start_dt.isoformat(timespec='minutes')
        rt['vas_end'] = end_dt.isoformat(timespec='minutes')
        rt['vas_prompt_day'] = datetime.now().date().isoformat()
        self._save_refusals_runtime(rt)
        return p

    def ensure_vas_report(self, when: datetime | None = None) -> Path:
        """Headless safety fallback; GUI normally asks the operator first."""
        p = self.vas_report()
        if p.exists():
            return p
        when = when or datetime.now(); op = operational_date(when)
        start = datetime.combine(op, datetime.min.time()).replace(hour=10)
        return self.create_new_vas(start, start + timedelta(days=1))

    def add_refusal(self,e:RefusalEntry,when:datetime|None=None)->tuple[Path,Path]:
        e.validate();when=when or datetime.now();op=operational_date(when)
        with exclusive_lock(self.refusal_dir/'script_lock.tmp',retries=10,delay=0.25):
            vas=self.vas_report(op)
            if not vas.exists():
                # Avoid nested lock by creating the default clean VAS in-place.
                start=datetime.combine(op,datetime.min.time()).replace(hour=10); end=start+timedelta(days=1)
                VasReportEngine(resource_path('VAS_base.docx')).create(
                    vas,[],start.strftime('%d-%m-%Y'),end.strftime('%d-%m-%Y'),
                    start_time=start.strftime('%H:%M'),end_time=end.strftime('%H:%M'))
                rt=self._load_refusals_runtime();rt['vas_start']=start.isoformat(timespec='minutes');rt['vas_end']=end.isoformat(timespec='minutes');self._save_refusals_runtime(rt)
            out=self.refusal_output();RefusalDocumentEngine(resource_path('Master_Template_Arnisi.docx')).create(out,e)
            self.store.add_refusal(e, op)
            VasReportEngine(resource_path('VAS_base.docx')).append(vas,e)
        # Same VBA rule: refusal remains committed even if Daily Activity is locked.
        self.last_activity_result=self._apply_activity(refusal_activity_plan(e))
        return out,vas

    # -------------------- ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ --------------------
    def _activity_writer(self):
        if self._activity_adapter is None:
            self._activity_adapter=ExcelComActivityAdapter(retries=10,delay=1.0)
        return self._activity_adapter

    def retry_pending_activity(self,limit:int=10)->int:
        workbook=clean(self.cfg.activity_workbook)
        if not workbook:
            return 0
        done=0
        adapter=self._activity_writer()
        for row in self.store.pending_activities(limit):
            plan=ActivityPlan(
                source=row['source'],target_cell=row['target_cell'],key=row['key'],log_sheet=row['log_sheet'],
                event_type=row.get('event_type','')
            )
            try:
                adapter.increment_once(workbook,plan)
                # False means the external AUTO_LOG already contains the transaction.
                self.store.mark_activity_done(plan.key);done+=1
            except Exception as exc:
                self.store.mark_activity_error(plan.key,str(exc))
                # Matching the VBA, do not block the current transaction on old pending work.
                break
        return done

    def _apply_activity(self,plan:ActivityPlan,*,retry_pending:bool=True)->ActivityResult:
        workbook=clean(self.cfg.activity_workbook)
        if not workbook:
            msg='Δεν έχει οριστεί ο Πίνακας Ημερήσιας Δραστηριότητας.'
            self.store.queue_activity(key=plan.key,source=plan.source,target_cell=plan.target_cell,log_sheet=plan.log_sheet,event_type=plan.event_type,error=msg)
            return ActivityResult(applied=False,queued=True,error=msg)
        try:
            if retry_pending:
                self.retry_pending_activity(10)
            applied=self._activity_writer().increment_once(workbook,plan)
            # If the same key had already been queued locally, external duplicate means success.
            self.store.mark_activity_done(plan.key)
            return ActivityResult(applied=applied,duplicate=not applied)
        except Exception as exc:
            msg=str(exc)
            self.store.queue_activity(key=plan.key,source=plan.source,target_cell=plan.target_cell,log_sheet=plan.log_sheet,event_type=plan.event_type,error=msg)
            return ActivityResult(applied=False,queued=True,error=msg)

    # -------------------- ΠΕΡΙΟΔΙΚΑ --------------------
    def periodicals_profile_path(self)->Path:
        if clean(self.cfg.periodicals_profile):
            return Path(self.cfg.periodicals_profile)
        # Runtime state must be writable. Copy the v10.3 snapshot only once.
        p=self.periodicals_dir/'periodicals_profile.json'
        if not p.exists(): shutil.copy2(resource_path('periodicals_profile.json'),p)
        return p

    def load_periodicals(self)->tuple[PeriodicalsEngine,dict,Path]:
        p=self.periodicals_profile_path();data=json.loads(p.read_text(encoding='utf-8'))
        packages=[Package(**x) for x in data['packages']]
        files=[PackageFile(**x) for x in data['files']]
        return PeriodicalsEngine(packages,files),data,p

    def save_periodicals(self,engine:PeriodicalsEngine,data:dict,path:Path)->None:
        data=dict(data)
        data['packages']=[asdict(p) for p in sorted(engine.packages.values(),key=lambda x:x.order)]
        data['files']=[asdict(f) for f in engine.files]
        tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)

    def _mutate_periodicals(self, fn):
        engine,data,p=self.load_periodicals()
        result=fn(engine)
        self.save_periodicals(engine,data,p)
        return result

    def create_periodical_package(self,name:str,root:str='') -> Package:
        return self._mutate_periodicals(lambda e:e.create_package(name,root=root))

    def rename_periodical_package(self,package_id:str,new_name:str) -> Package:
        return self._mutate_periodicals(lambda e:e.rename_package(package_id,new_name))

    def delete_periodical_package(self,package_id:str) -> None:
        self._mutate_periodicals(lambda e:e.delete_package(package_id))

    def periodical_catalog(self,package_id:str='') -> list[PackageFile]:
        engine,_,_=self.load_periodicals()
        active_sources={clean(f.source_path).casefold() for f in engine.package_files(package_id)} if package_id else set()
        return [f for f in engine.catalog_files() if clean(f.source_path).casefold() not in active_sources]

    def add_known_periodical_to_package(self,package_id:str,source_path:str) -> PackageFile:
        return self._mutate_periodicals(lambda e:e.add_known_file_to_package(package_id,source_path))

    def add_new_periodical_to_package(self,package_id:str,source_path:str,profile:str) -> PackageFile:
        return self._mutate_periodicals(lambda e:e.add_new_file_to_package(package_id,source_path,profile))

    def remove_periodical_from_package(self,package_id:str,source_path:str) -> None:
        self._mutate_periodicals(lambda e:e.remove_file_from_package(package_id,source_path))

    def prepare_periodical_package(self,package_id:str,when:datetime|None=None)->PreparationResult:
        when=when or datetime.now();allowed=operational_date(when);engine,data,p=self.load_periodicals()
        result=engine.prepare_next_package(package_id,allowed);self.save_periodicals(engine,data,p);return result

    def prepare_all_periodicals_for_date(self,target_date:date)->dict[str,list[str]]:
        """Equivalent to v10.3 PrepareAllFiles after user chooses the date."""
        engine,data,p=self.load_periodicals();result={}
        # The VBA deduplicates by actual source path globally. Keep that behavior.
        processed:set[str]=set()
        for pkg in engine.active_packages():
            paths=[]
            for f in engine.package_files(pkg.id):
                key=clean(f.source_path).upper()
                if key and key in processed: continue
                if key: processed.add(key)
                out,_created=engine.prepare_file(f,target_date)
                if out is not None: paths.append(str(out))
            result[pkg.id]=paths
        self.save_periodicals(engine,data,p);return result

    def prepare_all_periodicals(self,when:datetime|None=None)->dict[str,list[str]]:
        when=when or datetime.now();return self.prepare_all_periodicals_for_date(operational_date(when))

    def sync_periodical_package(self,package_id:str,when:datetime|None=None)->Path:
        when=when or datetime.now();allowed=operational_date(when);engine,data,p=self.load_periodicals()
        try:
            folder=engine.sync_package_folder(package_id,allowed)
        except (IncompletePackageError, FileNotFoundError, ValueError):
            # VBA saves LAST_FOLDER / managed-copy changes before reporting
            # an incomplete package, zero active files, or zero copied files.
            self.save_periodicals(engine,data,p)
            raise
        self.save_periodicals(engine,data,p);return folder

    def latest_periodical_paths(self,package_id:str,when:datetime|None=None)->list[Path]:
        when=when or datetime.now();allowed=operational_date(when);engine,data,p=self.load_periodicals();out=[]
        for f in engine.package_files(package_id):
            q=engine.latest_prepared_path(f,allowed)
            if q is not None:out.append(q)
        self.save_periodicals(engine,data,p);return out
