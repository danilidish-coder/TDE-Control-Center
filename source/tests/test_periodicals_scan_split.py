from pathlib import Path
from app.services.periodicals_unified import separate_series_file,series_folder_for_filename

def test_three_scan_folder_periodicals_are_separated(tmp_path:Path):
    common=tmp_path/"1. SCAN FOLDER REPORTS"
    legacy=common/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"/"03-10-2026"
    legacy.mkdir(parents=True)
    rows=[
        ("ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx","ΑΝΑΦΟΡΕΣ ΑΞ.ΥΠ.",b"a"),
        ("ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α. 03-10-2026 (μέχρι 06.00).xlsm","ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α.",b"b"),
        ("ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ 03-10-2026 (μέχρι 06.00).xlsx","ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ",b"c"),
    ]
    destinations=[]
    for name,folder,payload in rows:
        source=legacy/name
        source.write_bytes(payload)
        assert series_folder_for_filename(name)==folder
        dest=separate_series_file(source,common)
        destinations.append(dest)
        assert dest==common/folder/"2026"/"10. ΟΚΤΩΒΡΙΟΣ 2026"/name
        assert dest.read_bytes()==payload
        assert not source.exists()
    assert len({p.parents[2] for p in destinations})==3

def test_unknown_scan_file_is_not_moved(tmp_path:Path):
    common=tmp_path/"1. SCAN FOLDER REPORTS"; common.mkdir()
    source=common/"ΑΛΛΟ 03-10-2026.xlsx"; source.write_bytes(b"x")
    try:
        separate_series_file(source,common)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown file should be rejected")
    assert source.exists()
