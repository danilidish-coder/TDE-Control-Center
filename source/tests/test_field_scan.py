from dataclasses import asdict
from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from app.features.periodicals.engine import Package, PackageFile
from app.features.periodicals.unified_engine import UnifiedPeriodicalsEngine
from app.features.periodicals.service import PeriodicalsService
from app.features.periodicals.dates import destination_folder, replace_filename_date, series_folder_for_filename

NAMES = ['ΑΝΑΦΟΡΕΣ 31-12-2026 ΑΞ.ΥΠ..docx', 'ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α. 31-12-2026 (μέχρι 06.00).xlsm', 'ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ 31-12-2026.xlsx']


def setup_scan(tmp_path, day, split=False):
    root = tmp_path / '1. SCAN FOLDER REPORTS'
    rows = []
    for i, original in enumerate(NAMES):
        name = replace_filename_date(original, day)
        archive = root / series_folder_for_filename(name) if split else root
        folder = destination_folder(archive, day)
        if not split: folder /= day.strftime('%d-%m-%Y')
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / name
        source.write_bytes(f'SYNTHETIC TYPE {i}'.encode())
        rows.append(PackageFile('P1', name, str(source), archive_root=str(archive), folder_layout='YEAR_MONTH'))
    package = Package('P1', 'SYNTHETIC', root=str(tmp_path / 'out'))
    return root, rows, package


@pytest.mark.parametrize('day,target', [(date(2026,10,22),date(2026,10,23)),(date(2026,10,31),date(2026,11,1)),(date(2026,12,31),date(2027,1,1))])
@pytest.mark.parametrize('split', [False,True])
def test_scan_three_types_share_one_daily_folder_and_originals_are_preserved(tmp_path, day, target, split):
    root, rows, pkg = setup_scan(tmp_path,day,split)
    originals = {Path(f.source_path):Path(f.source_path).read_bytes() for f in rows}
    engine = UnifiedPeriodicalsEngine([pkg],rows)
    result = engine.prepare_next_package('P1',target)
    assert len(result.prepared) == 3 and not result.failed
    expected = destination_folder(root,target) / target.strftime('%d-%m-%Y')
    assert {p.parent for p in result.prepared} == {expected}
    for i, name in enumerate(NAMES):
        assert (expected/replace_filename_date(name,target)).read_bytes() == f'SYNTHETIC TYPE {i}'.encode()
    assert all(p.read_bytes()==value for p,value in originals.items())
    repeated = engine.prepare_next_package('P1',target)
    assert repeated.already_current and not repeated.prepared


def test_shared_root_selects_latest_of_each_type_instead_of_latest_unrelated_file(tmp_path):
    root, rows, pkg = setup_scan(tmp_path,date(2026,12,31))
    engine = UnifiedPeriodicalsEngine([pkg],rows)
    for i, f in enumerate(rows):
        folder = destination_folder(root,date(2027,1,i+1)) / f'0{i+1}-01-2027'
        folder.mkdir(parents=True)
        (folder/replace_filename_date(NAMES[i],date(2027,1,i+1))).write_bytes(f'LATEST TYPE {i}'.encode())
    for i, f in enumerate(rows):
        day, source = engine.latest_existing_prepared(f,date(2027,1,3))
        assert day == date(2027,1,i+1)
        assert source.read_bytes() == f'LATEST TYPE {i}'.encode()


def test_same_day_old_split_files_are_copied_to_canonical_day_without_deleting_legacy(tmp_path):
    root, rows, pkg = setup_scan(tmp_path,date(2026,12,31),True)
    engine = UnifiedPeriodicalsEngine([pkg],rows)
    result = engine.prepare_next_package('P1',date(2026,12,31))
    assert len(result.prepared)==3
    assert all(Path(f.source_path).exists() for f in rows)
    assert {p.parent for p in result.prepared} == {destination_folder(root,date(2026,12,31))/'31-12-2026'}


def test_dynamic_profile_prepares_three_members_in_two_packages_without_duplicate_copies(tmp_path,monkeypatch):
    import app.features.periodicals.service as module
    monkeypatch.setattr(module,'runtime_root',lambda:tmp_path/'runtime')
    root, rows, pkg = setup_scan(tmp_path,date(2026,12,31))
    second=Package('P2','SECOND',root=str(tmp_path/'out'))
    clones=[PackageFile(**{**asdict(f),'package_id':'P2'}) for f in rows]
    service=PeriodicalsService()
    service.profile.write_text(json.dumps({'packages':[asdict(pkg),asdict(second)],'files':[asdict(f) for f in rows+clones]},ensure_ascii=False),encoding='utf-8')
    result=service.prepare_all_for_date(date(2027,1,1))
    assert len(result['P1'])==len(result['P2'])==3
    assert set(result['P1'])==set(result['P2'])
    assert len(list((destination_folder(root,date(2027,1,1))/'01-01-2027').iterdir()))==3


def test_latest_manually_renamed_scan_series_is_recognized(tmp_path):
    root, rows, pkg=setup_scan(tmp_path,date(2026,12,31))
    engine=UnifiedPeriodicalsEngine([pkg],rows)
    changed=Path(rows[1].source_path).with_name('ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΑ Γ.Α. 01-01-2027 (έως 06.00), TEST.xlsm')
    changed.write_bytes(b'MANUAL LATEST')
    day, selected=engine.latest_existing_prepared(rows[1],date(2027,1,1))
    assert day==date(2027,1,1) and selected==changed
