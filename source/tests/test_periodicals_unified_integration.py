from datetime import date
from pathlib import Path

from app.services.periodicals_engine import (
    Package, PackageFile, PROFILE_AS_IS, PROFILE_DAILY_FOLDER, PROFILE_SAME_FOLDER,
)
from app.services.periodicals_unified_engine import UnifiedPeriodicalsEngine, PROFILE_UNIFIED


def _pkg(root, pid="P1", name="ERMIS 1"):
    return Package(id=pid, name=name, root=str(root), active=True, order=1)


def test_old_month_profile_migrates_and_real_latest_name_drives_next(tmp_path):
    root = tmp_path / "REPORT"
    month = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026"
    month.mkdir(parents=True)
    latest = month / "ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_03_10_2026.xls"
    latest.write_bytes(b"v1")
    row = PackageFile("P1", latest.name, str(latest), True, PROFILE_SAME_FOLDER,
                      "IGNORED_TEMPLATE.xls", "", "", str(root), "", "BAT_MONTH", "")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [row])
    assert row.profile == PROFILE_UNIFIED
    assert row.name_template == ""
    assert row.folder_layout == "YEAR_MONTH"

    manual = latest.with_name("ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ ΝΕΟ,_03_10_2026.xls")
    latest.rename(manual)
    manual.write_bytes(b"user-edit")
    result = engine.prepare_next_package("P1", date(2026, 10, 4))
    out = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ ΝΕΟ,_04_10_2026.xls"
    assert result.prepared == [out]
    assert out.read_bytes() == b"user-edit"


def test_old_scan_daily_seed_stays_but_next_goes_to_own_series(tmp_path):
    scan = tmp_path / "1. SCAN FOLDER REPORTS"
    legacy = scan / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "03-10-2026"
    legacy.mkdir(parents=True)
    source = legacy / "ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx"
    source.write_bytes(b"seed")
    row = PackageFile("P1", source.name, str(source), True, PROFILE_DAILY_FOLDER,
                      "template", "", "", str(scan), "", "BAT_DAILY", "")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [row])
    expected_root = scan / "ΑΝΑΦΟΡΕΣ ΑΞ.ΥΠ."
    assert Path(row.archive_root) == expected_root

    result = engine.prepare_next_package("P1", date(2026, 10, 4))
    out = expected_root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "ΑΝΑΦΟΡΕΣ 04-10-2026 ΑΞ.ΥΠ..docx"
    assert out in result.prepared
    assert out.read_bytes() == b"seed"
    assert source.exists()


def test_three_scan_periodicals_become_three_independent_roots(tmp_path):
    scan = tmp_path / "1. SCAN FOLDER REPORTS"
    day = scan / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "03-10-2026"
    day.mkdir(parents=True)
    names = [
        "ΑΝΑΦΟΡΕΣ 03-10-2026 ΑΞ.ΥΠ..docx",
        "ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α. 03-10-2026 (μέχρι 06.00).xlsm",
        "ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ 03-10-2026 (μέχρι 06.00).xlsx",
    ]
    rows = []
    for name in names:
        source = day / name
        source.write_bytes(name.encode())
        rows.append(PackageFile("P1", name, str(source), True, PROFILE_DAILY_FOLDER,
                                "", "", "", str(scan), "", "BAT_DAILY", ""))
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], rows)
    assert {Path(row.archive_root).name for row in rows} == {
        "ΑΝΑΦΟΡΕΣ ΑΞ.ΥΠ.",
        "ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α.",
        "ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ",
    }
    result = engine.prepare_next_package("P1", date(2026, 10, 4))
    assert len(result.prepared) == 3


def test_new_dated_orphan_is_moved_into_year_month_at_registration(tmp_path):
    root = tmp_path / "SARISA"
    root.mkdir()
    source = root / "ΗΜΕΡΗΣΙΟ 2026-10-03.xls"
    source.write_bytes(b"seed")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [])
    row = engine.add_new_file_to_package("P1", str(source), date(2026, 10, 3))
    target = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / source.name
    assert Path(row.source_path) == target
    assert target.exists()
    assert not source.exists()


def test_new_undated_orphan_gets_first_date_once_then_copies_latest(tmp_path):
    root = tmp_path / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ"
    root.mkdir()
    source = root / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ.xlsx"
    source.write_bytes(b"day1")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [])
    row = engine.add_new_file_to_package("P1", str(source), date(2026, 10, 3))
    first = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ 03-10-2026.xlsx"
    assert Path(row.source_path) == first
    assert first.read_bytes() == b"day1"

    first.write_bytes(b"user-changed")
    result = engine.prepare_next_package("P1", date(2026, 10, 4))
    second = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ 04-10-2026.xlsx"
    assert result.prepared == [second]
    assert second.read_bytes() == b"user-changed"


def test_old_as_is_definition_no_longer_stays_as_is(tmp_path):
    root = tmp_path / "DAILY"
    root.mkdir()
    source = root / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ.xlsx"
    source.write_bytes(b"live")
    row = PackageFile("P1", source.name, str(source), True, PROFILE_AS_IS,
                      "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ {DD-MM-YYYY}.xlsx", "", "", str(root), "", "AS_IS", "")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [row])
    assert row.profile == PROFILE_UNIFIED
    result = engine.prepare_next_package("P1", date(2026, 10, 3))
    target = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ 03-10-2026.xlsx"
    assert target in result.prepared
    assert target.exists()
    assert not source.exists()


def test_package_sync_keeps_only_latest_managed_copy(tmp_path):
    root = tmp_path / "periodic"
    root.mkdir()
    source = root / "REPORT 03-10-2026.xlsx"
    source.write_bytes(b"3")
    engine = UnifiedPeriodicalsEngine([_pkg(tmp_path / "packages")], [])
    engine.add_new_file_to_package("P1", str(source), date(2026, 10, 3))
    engine.prepare_next_package("P1", date(2026, 10, 4))
    folder = engine.sync_package_folder("P1", date(2026, 10, 4))
    p4 = folder / "REPORT 04-10-2026.xlsx"
    assert p4.exists()

    engine.prepare_next_package("P1", date(2026, 10, 5))
    engine.sync_package_folder("P1", date(2026, 10, 5))
    p5 = folder / "REPORT 05-10-2026.xlsx"
    assert p5.exists()
    assert not p4.exists()
    assert (root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026" / "REPORT 04-10-2026.xlsx").exists()


def test_known_catalog_file_is_normalized_when_added_to_second_package(tmp_path):
    root = tmp_path / "REPORT"
    month = root / "2026" / "10. ΟΚΤΩΒΡΙΟΣ 2026"
    month.mkdir(parents=True)
    source = month / "REPORT 03-10-2026.xlsx"
    source.write_bytes(b"x")
    p1 = _pkg(tmp_path / "packages1", "P1", "ONE")
    p2 = _pkg(tmp_path / "packages2", "P2", "TWO")
    original = PackageFile("P1", source.name, str(source), True, PROFILE_SAME_FOLDER,
                           "REPORT {DD-MM-YYYY}.xlsx", "", "", str(root), "", "BAT_MONTH", "")
    engine = UnifiedPeriodicalsEngine([p1, p2], [original])

    clone = engine.add_known_file_to_package("P2", str(source))

    assert clone.profile == PROFILE_UNIFIED
    assert clone.name_template == ""
    assert clone.folder_layout == "YEAR_MONTH"
    assert Path(clone.archive_root) == root
