from datetime import date
from pathlib import Path

from app.services.periodicals_engine import (
    Package,
    PackageFile,
    PeriodicalsEngine,
    PROFILE_AS_IS,
    PROFILE_DAILY_FOLDER,
    PROFILE_SAME_FOLDER,
    apply_name_template,
    build_daily_folder,
    build_month_folder,
)


def test_periodicals_naming_and_folder_layout_are_v103_compatible(tmp_path):
    d = date(2026, 8, 22)
    root = tmp_path / "archive"

    assert build_month_folder(root, d) == root / "2026" / "8. ΑΥΓΟΥΣΤΟΣ 2026"
    assert build_daily_folder(root, d) == root / "2026" / "8. ΑΥΓΟΥΣΤΟΣ 2026" / "22-08-2026"
    assert apply_name_template("ΑΤ_{DD_MM_YYYY}.xls", d) == "ΑΤ_22_08_2026.xls"
    assert apply_name_template("REPORT {YYYY-MM-DD}.xlsx", d) == "REPORT 2026-08-22.xlsx"
    assert apply_name_template("{DD-MM-YY}+DAILY.doc", d) == "22-08-26+DAILY.doc"


def test_periodicals_prepare_and_sync_keeps_only_latest_managed_package_copy(tmp_path):
    archive_root = tmp_path / "archive"
    package_root = tmp_path / "packages"
    d1 = date(2026, 8, 21)
    d2 = date(2026, 8, 22)

    month = build_month_folder(archive_root, d1)
    month.mkdir(parents=True)
    source1 = month / "ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_21_08_2026.xls"
    source1.write_bytes(b"day-21")

    pkg = Package(id="PKG004", name="ERMIS 1", root=str(package_root), active=True, order=1)
    row = PackageFile(
        package_id="PKG004",
        name=source1.name,
        source_path=str(source1),
        active=True,
        profile=PROFILE_SAME_FOLDER,
        name_template="ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_{DD_MM_YYYY}.xls",
        archive_root=str(archive_root),
        folder_layout="BAT_MONTH",
    )
    engine = PeriodicalsEngine([pkg], [row])

    result = engine.prepare_next_package("PKG004", d2)
    expected2 = build_month_folder(archive_root, d2) / "ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_22_08_2026.xls"
    assert result.target_date == d2
    assert expected2.exists() and expected2.read_bytes() == b"day-21"

    package_folder = engine.sync_package_folder("PKG004", d2)
    managed2 = package_folder / expected2.name
    assert managed2.exists()

    # Simulate the next prepared day without touching/removing source/archive history.
    d3 = date(2026, 8, 23)
    result2 = engine.prepare_next_package("PKG004", d3)
    expected3 = build_month_folder(archive_root, d3) / "ΑΤ_ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ_23_08_2026.xls"
    assert result2.target_date == d3
    assert expected3.exists()

    engine.sync_package_folder("PKG004", d3)
    managed3 = package_folder / expected3.name
    assert managed3.exists()
    assert managed2.exists(), "Το Βήμα 3 διατηρεί παλιότερα και μη απεσταλμένα αντίγραφα."

    # The historical archive/source must remain untouched.
    assert source1.exists()
    assert expected2.exists()
    assert expected3.exists()


def test_periodicals_as_is_is_reused_without_date_renaming_or_source_change(tmp_path):
    package_root = tmp_path / "packages"
    source = tmp_path / "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ.xlsx"
    source.write_bytes(b"live-file")
    original_mtime = source.stat().st_mtime_ns

    pkg = Package(id="PKG004", name="ERMIS 1", root=str(package_root), active=True, order=1)
    row = PackageFile(
        package_id="PKG004",
        name=source.name,
        source_path=str(source),
        active=True,
        profile=PROFILE_AS_IS,
        name_template="ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ {DD-MM-YYYY}.xlsx",
        folder_layout="AS_IS",
    )
    engine = PeriodicalsEngine([pkg], [row])
    allowed = date(2026, 9, 25)

    result = engine.prepare_next_package("PKG004", allowed)
    assert result.target_date == allowed
    assert result.prepared == []
    assert result.skipped_existing == [source]
    assert row.prepared_path == str(source)
    assert Path(row.prepared_path).name == "ΗΜΕΡΗΣΙΑ ΚΙΝΗΣΗ.xlsx"
    assert source.read_bytes() == b"live-file"
    assert source.stat().st_mtime_ns == original_mtime

    package_folder = engine.sync_package_folder("PKG004", allowed)
    copied = package_folder / source.name
    assert copied.exists() and copied.read_bytes() == b"live-file"
    assert source.exists(), "Το πρωτότυπο AS-IS αρχείο δεν πρέπει να μετακινείται/διαγράφεται."
