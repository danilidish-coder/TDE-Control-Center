from __future__ import annotations
from datetime import date
from pathlib import Path
import pytest

from app.services.periodicals_unified import create_next_from_latest,destination_folder,filename_date,latest_file,move_orphan_into_archive,replace_filename_date

@pytest.mark.parametrize(("name","expected"),[
 ("ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_30_09_2026.xls","ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_01_10_2026.xls"),
 ("ΗΜΕΡΗΣΙΟ 2026-09-30.xls","ΗΜΕΡΗΣΙΟ 2026-10-01.xls"),
 ("30-09-26+DAILY ACTIVITY+BCP KRYSTALLOPIGI.doc","01-10-26+DAILY ACTIVITY+BCP KRYSTALLOPIGI.doc"),
 ("ΝΕΑ ΠΡΩΙΝΗ, ΑΝΑΦΟΡΑ_30-09-2026 (μέχρι 06.00).xlsm","ΝΕΑ ΠΡΩΙΝΗ, ΑΝΑΦΟΡΑ_01-10-2026 (μέχρι 06.00).xlsm"),
])
def test_only_date_text_changes(name,expected):
    assert replace_filename_date(name,date(2026,10,1))==expected

def test_orphan_is_moved_into_year_month_without_renaming(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"; root.mkdir()
    orphan=root/"ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx"; orphan.write_bytes(b"original")
    moved=move_orphan_into_archive(orphan)
    assert moved==root/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"/orphan.name
    assert moved.read_bytes()==b"original"
    assert not orphan.exists()

def test_next_file_is_byte_for_byte_copy_and_uses_next_day(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"
    source_dir=destination_folder(root,date(2026,10,3)); source_dir.mkdir(parents=True)
    source=source_dir/"ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx"
    payload=b"changed workbook or document bytes"; source.write_bytes(payload)
    created=create_next_from_latest(root)
    assert created==root/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"/"ΑΝΑΦΟΡΕΣ 04-10-2026 ΑΞ.ΥΠ..docx"
    assert created.read_bytes()==payload

def test_manual_filename_change_is_inherited_from_real_latest_file(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"
    folder=destination_folder(root,date(2026,10,3)); folder.mkdir(parents=True)
    source=folder/"ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α. 03-10-2026 (μέχρι 06.00).xlsm"; source.write_bytes(b"v1")
    day4=create_next_from_latest(root)
    manual=day4.with_name("ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΑ Γ.Α. 04-10-2026 (έως 06.00), ΤΔΕ.xlsm")
    day4.rename(manual); manual.write_bytes(b"user changed content")
    day5=create_next_from_latest(root)
    assert day5.name=="ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΑ Γ.Α. 05-10-2026 (έως 06.00), ΤΔΕ.xlsm"
    assert day5.read_bytes()==b"user changed content"

def test_month_change_creates_new_month_folder(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"
    folder=destination_folder(root,date(2026,10,31)); folder.mkdir(parents=True)
    (folder/"ΗΜΕΡΗΣΙΟ 2026-10-31.xls").write_bytes(b"x")
    created=create_next_from_latest(root)
    assert created==root/"2026"/"11. ΝΟΕΜΒΡΙΟΣ 2026"/"ΗΜΕΡΗΣΙΟ 2026-11-01.xls"

def test_year_change_creates_new_year_and_january_folder(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"
    folder=destination_folder(root,date(2026,12,31)); folder.mkdir(parents=True)
    (folder/"ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_31_12_2026.xls").write_bytes(b"x")
    created=create_next_from_latest(root)
    assert created==root/"2027"/"1. ΙΑΝΟΥΑΡΙΟΣ 2027"/"ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_01_01_2027.xls"

def test_latest_is_decided_by_filename_date_not_modified_time(tmp_path:Path):
    root=tmp_path/"ΠΕΡΙΟΔΙΚΟ"
    old_dir=destination_folder(root,date(2026,9,30)); new_dir=destination_folder(root,date(2026,10,1))
    old_dir.mkdir(parents=True); new_dir.mkdir(parents=True)
    old=old_dir/"REPORT 30-09-2026.docx"; new=new_dir/"REPORT 01-10-2026.docx"
    old.write_bytes(b"old"); new.write_bytes(b"new"); old.touch()
    value,selected=latest_file(root)
    assert value==date(2026,10,1)
    assert selected==new

def test_invalid_or_ambiguous_filename_is_rejected():
    with pytest.raises(ValueError):
        filename_date("ΠΕΡΙΟΔΙΚΟ ΧΩΡΙΣ ΗΜΕΡΟΜΗΝΙΑ.xlsx")
    with pytest.raises(ValueError):
        filename_date("REPORT 01-10-2026 έως 02-10-2026.xlsx")
