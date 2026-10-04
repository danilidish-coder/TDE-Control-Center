from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.docgen.common import operational_date
from app.services.periodicals_engine import Package, PackageFile, PROFILE_DAILY_FOLDER
from app.services.periodicals_unified import (
    destination_folder, filename_date, replace_filename_date,
)
from app.services.periodicals_unified_engine import UnifiedPeriodicalsEngine


def _pkg(root, pid="P1", name="PKG"):
    return Package(id=pid, name=name, root=str(root), active=True, order=1)


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        ("REPORT 31-10-2026.xlsx", date(2026,11,1), "REPORT 01-11-2026.xlsx"),
        ("REPORT_2026_12_31.xls", date(2027,1,1), "REPORT_2027_01_01.xls"),
        ("31-12-26+DAILY ACTIVITY.doc", date(2027,1,1), "01-01-27+DAILY ACTIVITY.doc"),
        ("Α,Β_03-10-2026__Χ+Ψ..xlsx", date(2026,10,4), "Α,Β_04-10-2026__Χ+Ψ..xlsx"),
        ("REPORT.2026.10.03.xlsx", date(2026,10,4), "REPORT.2026.10.04.xlsx"),
    ],
)
def test_filename_changes_only_date_and_keeps_punctuation(source, target, expected):
    assert replace_filename_date(source, target) == expected


def test_invalid_and_two_different_dates_are_rejected():
    with pytest.raises(ValueError):
        filename_date("ΧΩΡΙΣ ΗΜΕΡΟΜΗΝΙΑ.xlsx")
    with pytest.raises(ValueError):
        filename_date("ΑΠΟ 03-10-2026 ΕΩΣ 04-10-2026.xlsx")


def test_month_folder_convention_including_may_is_stable(tmp_path):
    assert destination_folder(tmp_path, date(2026,5,1)) == tmp_path/"2026"/"5. ΜΑΙΟΣ 2026"
    assert destination_folder(tmp_path, date(2026,10,1)) == tmp_path/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"


def test_existing_target_is_never_overwritten(tmp_path):
    root=tmp_path/"R"; root.mkdir()
    source=root/"REPORT 03-10-2026.xlsx"; source.write_bytes(b"source")
    engine=UnifiedPeriodicalsEngine([_pkg(tmp_path/"packages")],[])
    engine.add_new_file_to_package("P1",str(source),date(2026,10,3))
    target=destination_folder(root,date(2026,10,4))/"REPORT 04-10-2026.xlsx"
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b"already-edited")
    result=engine.prepare_next_package("P1",date(2026,10,4))
    assert target.read_bytes()==b"already-edited"
    assert result.already_current is True
    assert result.prepared==[]


def test_latest_date_wins_even_if_older_file_has_newer_mtime(tmp_path):
    root=tmp_path/"R"
    d2=destination_folder(root,date(2026,10,2)); d3=destination_folder(root,date(2026,10,3))
    d2.mkdir(parents=True,exist_ok=True); d3.mkdir(parents=True,exist_ok=True)
    old=d2/"REPORT 02-10-2026.xlsx"; latest=d3/"REPORT 03-10-2026.xlsx"
    old.write_bytes(b"old"); latest.write_bytes(b"latest")
    old.touch()
    row=PackageFile("P1",latest.name,str(latest),archive_root=str(root))
    engine=UnifiedPeriodicalsEngine([_pkg(tmp_path/"packages")],[row])
    when,path=engine.latest_existing_prepared(row,date(2026,10,3))
    assert when==date(2026,10,3)
    assert path==latest


def test_leap_day_and_year_boundary(tmp_path):
    root=tmp_path/"R"; root.mkdir()
    source=root/"REPORT 28-02-2028.xlsx"; source.write_bytes(b"leap")
    engine=UnifiedPeriodicalsEngine([_pkg(tmp_path/"packages")],[])
    engine.add_new_file_to_package("P1",str(source),date(2028,2,28))
    r1=engine.prepare_next_package("P1",date(2028,2,29))
    assert r1.prepared[0].name=="REPORT 29-02-2028.xlsx"
    r2=engine.prepare_next_package("P1",date(2028,3,1))
    assert r2.prepared[0] == root/"2028"/"3. ΜΑΡΤΙΟΣ 2028"/"REPORT 01-03-2028.xlsx"


def test_100_sequential_days_keep_real_latest_content_and_structure(tmp_path):
    root=tmp_path/"R"; root.mkdir()
    source=root/"REPORT,_01-10-2026__A.xlsx"; source.write_bytes(b"seed")
    engine=UnifiedPeriodicalsEngine([_pkg(tmp_path/"packages")],[])
    engine.add_new_file_to_package("P1",str(source),date(2026,10,1))
    current=date(2026,10,1)
    for i in range(1,101):
        target=current+timedelta(days=1)
        latest_date,latest=engine.latest_existing_prepared(engine.files[0],current)
        latest.write_bytes(f"content-{i}".encode())
        result=engine.prepare_next_package("P1",target)
        assert len(result.prepared)==1
        created=result.prepared[0]
        assert filename_date(created.name)[0]==target
        assert created.read_bytes()==f"content-{i}".encode()
        assert created.parent==destination_folder(root,target)
        current=target


def test_three_scan_series_never_share_future_archive_root(tmp_path):
    scan=tmp_path/"1. SCAN FOLDER REPORTS"
    day=scan/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"/"03-10-2026"; day.mkdir(parents=True)
    names=[
      "ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx",
      "ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α. 03-10-2026 (μέχρι 06.00).xlsm",
      "ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ 03-10-2026 (μέχρι 06.00).xlsx",
    ]
    rows=[]
    for name in names:
        p=day/name; p.write_bytes(b"x")
        rows.append(PackageFile("P1",name,str(p),True,PROFILE_DAILY_FOLDER,"","","",str(scan),"","BAT_DAILY",""))
    engine=UnifiedPeriodicalsEngine([_pkg(tmp_path/"packages")],rows)
    result=engine.prepare_next_package("P1",date(2026,10,4))
    assert len(result.prepared)==3
    assert len({p.parents[2] for p in result.prepared})==3


def test_cutoff_1000_rule_remains_unchanged():
    assert operational_date(datetime(2026,10,3,9,59))==date(2026,10,2)
    assert operational_date(datetime(2026,10,3,10,0))==date(2026,10,3)


def test_ui_contains_no_old_profile_question():
    root=Path(__file__).resolve().parents[1]
    ui=(root/"app/ui/periodicals_page.py").read_text(encoding="utf-8")
    assert "Πώς οργανώνεται το αρχείο;" not in ui
    assert "ΜΗΝΙΑΙΟ BAT" not in ui
    assert "ΗΜΕΡΗΣΙΟ BAT" not in ui
    assert 'self.service.add_new(pid, src)' in ui
