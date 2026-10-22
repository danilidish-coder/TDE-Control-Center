from datetime import date, datetime
from pathlib import Path

from app.features.periodicals.engine import Package, PackageFile
from app.features.periodicals.unified_engine import UnifiedPeriodicalsEngine


def test_repeated_step3_preserves_edited_unsent_and_inactive_copies(tmp_path):
    source=tmp_path/'archive'/'REPORT 21-10-2026.xlsx';source.parent.mkdir();source.write_bytes(b'SOURCE')
    row=PackageFile('P','REPORT',str(source),archive_root=str(source.parent))
    engine=UnifiedPeriodicalsEngine([Package('P','PACKAGE',root=str(tmp_path/'packages'))],[row])
    folder=engine.sync_package_folder('P',date(2026,10,22))
    copy=folder/source.name;copy.write_bytes(b'UNSENT USER EDITS')
    assert engine.sync_package_folder('P',date(2026,10,22))==folder
    assert copy.read_bytes()==b'UNSENT USER EDITS'
    row.active=False
    other=source.with_name('OTHER 21-10-2026.xlsx');other.write_bytes(b'OTHER')
    engine.files.append(PackageFile('P',other.name,str(other),archive_root=str(other.parent)))
    engine.sync_package_folder('P',date(2026,10,22))
    assert copy.read_bytes()==b'UNSENT USER EDITS'


def test_step1_new_cycle_preserves_old_packages_and_does_not_roll_on_step3(tmp_path,monkeypatch):
    import app.features.periodicals.service as module
    from app.features.periodicals.service import PeriodicalsService
    monkeypatch.setattr(module,'runtime_root',lambda:tmp_path/'runtime')
    source=tmp_path/'archive'/'REPORT 21-10-2026.xlsx';source.parent.mkdir();source.write_bytes(b'SOURCE')
    row=PackageFile('P',source.name,str(source),archive_root=str(source.parent))
    engine=UnifiedPeriodicalsEngine([Package('P','PACKAGE',root=str(tmp_path/'packages'))],[row])
    service=PeriodicalsService();service.save(engine,{})
    service.prepare_package('P',datetime(2026,10,22,12))
    first=service.sync_package('P',datetime(2026,10,22,12))
    (first/'manual-unsent.txt').write_bytes(b'KEEP')
    copy=next(first.glob('*.xlsx'));copy.write_bytes(b'EDITED')
    assert service.sync_package('P',datetime(2026,10,22,12))==first
    assert copy.read_bytes()==b'EDITED'
    service.prepare_package('P',datetime(2026,10,23,12))
    second=service.sync_package('P',datetime(2026,10,23,12))
    assert second != first and second.name=='2026-10-23'
    assert (first/'manual-unsent.txt').read_bytes()==b'KEEP'
    assert copy.read_bytes()==b'EDITED'
    assert len(list(second.glob('*.xlsx')))==1


def test_step3_stays_enabled_after_repetition_and_restart(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    import app.features.periodicals.service as module
    from app.features.periodicals.service import PeriodicalsService
    from app.features.periodicals.page import PeriodicalsPage
    monkeypatch.setattr(module,'runtime_root',lambda:tmp_path/'runtime')
    source=tmp_path/'archive'/'REPORT 21-10-2026.xlsx';source.parent.mkdir();source.write_bytes(b'SOURCE')
    service=PeriodicalsService()
    engine=UnifiedPeriodicalsEngine([Package('P','PACKAGE',root=str(tmp_path/'packages'))],[PackageFile('P',source.name,str(source),archive_root=str(source.parent))])
    engine.package_cycles['P']='2026-10-22';service.save(engine,{})
    monkeypatch.setattr(service,'open_path',lambda path:None)
    monkeypatch.setattr(QMessageBox,'information',lambda *args:QMessageBox.Ok)
    app=QApplication.instance() or QApplication([])
    page=PeriodicalsPage(service)
    try:
        assert page.ready_btn.isEnabled()
        page.sync();assert page.ready_btn.isEnabled()
        page.sync();assert page.ready_btn.isEnabled()
        page.refresh();assert page.ready_btn.isEnabled()
    finally:page.close()


def test_partial_copy_failure_cleans_only_owned_copy_and_never_overwrites_existing(tmp_path,monkeypatch):
    import shutil
    import pytest
    from app.features.periodicals.engine import PeriodicalsEngine
    source=tmp_path/'source.xlsx';source.write_bytes(b'SOURCE')
    destination=tmp_path/'working.xlsx'
    def fail(input_file,output):
        output.write(b'PARTIAL')
        raise OSError('synthetic disk full')
    monkeypatch.setattr(shutil,'copyfileobj',fail)
    with pytest.raises(OSError):PeriodicalsEngine._copy_working_document(source,destination)
    assert not destination.exists() and source.read_bytes()==b'SOURCE'
    destination.write_bytes(b'UNSENT')
    PeriodicalsEngine._copy_working_document(source,destination)
    assert destination.read_bytes()==b'UNSENT'


def test_new_profile_keeps_legacy_package_constructor_compatible(tmp_path,monkeypatch):
    import json
    import app.features.periodicals.service as module
    from app.features.periodicals.service import PeriodicalsService
    monkeypatch.setattr(module,'runtime_root',lambda:tmp_path/'runtime')
    service=PeriodicalsService()
    engine=UnifiedPeriodicalsEngine([Package('P','TEST',root=str(tmp_path/'out'))],[])
    engine.package_cycles['P']='2026-10-22'
    service.save(engine,{})
    data=json.loads(service.profile.read_text(encoding='utf-8'))
    assert Package(**data['packages'][0]).id=='P'
    loaded,_,_=service.load()
    assert loaded.package_cycles=={'P':'2026-10-22'}
