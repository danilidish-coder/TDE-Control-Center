from contextlib import contextmanager
import json
from pathlib import Path

import pytest

from app.features.periodicals.service import PeriodicalsService


def setup_profile(tmp_path,monkeypatch):
    import app.features.periodicals.service as module
    monkeypatch.setattr(module,'runtime_root',lambda:tmp_path/'runtime')
    old=tmp_path/'DA'/'Περιοδικά SHARED_FILES'/'ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ'
    old.mkdir(parents=True)
    for name,body in [('2025/12. ΔΕΚΕΜΒΡΙΟΣ 2025/31-12-2025/old.xlsx',b'HISTORY'),('2026/10. ΟΚΤΩΒΡΙΟΣ 2026/22-10-2026/ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ 22-10-2026.xlsx',b'CURRENT')]:
        p=old/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    service=PeriodicalsService()
    current=next(old.rglob('ΗΜΕΡΗΣΙΑ*'))
    data={'custom':'keep','packages':[{'id':'P','name':'TEST','root':str(tmp_path/'packages')}], 'files':[{'package_id':'P','name':current.name,'source_path':str(current),'prepared_path':str(current),'archive_root':str(old)}]}
    service.profile.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    return service,old,data


def test_entire_daily_folder_moves_one_level_with_history_and_dynamic_references(tmp_path,monkeypatch):
    service,old,data=setup_profile(tmp_path,monkeypatch)
    original={p.relative_to(old):p.read_bytes() for p in old.rglob('*') if p.is_file()}
    service.load()  # Merely reading the profile must never move real data.
    assert old.exists()
    result=service.relocate_daily_movement('P')
    target=old.parent.parent/old.name
    assert result['moved'] and not old.exists() and target.is_dir()
    assert {p.relative_to(target):p.read_bytes() for p in target.rglob('*') if p.is_file()}==original
    saved=json.loads(service.profile.read_text(encoding='utf-8'))
    assert saved['custom']=='keep'
    assert Path(saved['files'][0]['archive_root'])==target
    assert Path(saved['files'][0]['source_path']).is_file()
    assert service.relocate_daily_movement('P') is None


def test_collision_leaves_both_complete_folders_and_profile_untouched(tmp_path,monkeypatch):
    service,old,data=setup_profile(tmp_path,monkeypatch)
    target=old.parent.parent/old.name;target.mkdir();(target/'unsent.xlsx').write_bytes(b'KEEP')
    before=service.profile.read_bytes()
    with pytest.raises(FileExistsError):service.relocate_daily_movement('P')
    assert old.is_dir() and (target/'unsent.xlsx').read_bytes()==b'KEEP'
    assert service.profile.read_bytes()==before


def test_profile_write_failure_rolls_back_the_whole_directory_rename(tmp_path,monkeypatch):
    import app.features.periodicals.service as module
    service,old,data=setup_profile(tmp_path,monkeypatch)
    before=service.profile.read_bytes()
    @contextmanager
    def fail(path):
        raise PermissionError('synthetic profile locked')
        yield
    monkeypatch.setattr(module,'atomic_output',fail)
    with pytest.raises(PermissionError):service.relocate_daily_movement('P')
    assert old.is_dir() and not (old.parent.parent/old.name).exists()
    assert service.profile.read_bytes()==before


def test_already_moved_folder_reconciles_saved_profile_without_moving_files(tmp_path,monkeypatch):
    service,old,data=setup_profile(tmp_path,monkeypatch)
    target=old.parent.parent/old.name;old.rename(target)
    result=service.relocate_daily_movement('P')
    assert not result['moved']
    assert Path(json.loads(service.profile.read_text(encoding='utf-8'))['files'][0]['source_path']).exists()


def test_windows_junction_is_not_automatically_moved(tmp_path,monkeypatch):
    service,old,_=setup_profile(tmp_path,monkeypatch)
    before=service.profile.read_bytes()
    monkeypatch.setattr(Path,'is_junction',lambda p:p==old,raising=False)
    with pytest.raises(ValueError):service.relocate_daily_movement('P')
    assert old.is_dir() and service.profile.read_bytes()==before
