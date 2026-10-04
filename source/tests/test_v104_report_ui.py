from pathlib import Path


def test_report_actions_are_clearly_separated_everywhere():
    root = Path(__file__).resolve().parents[1]
    fines = (root / "app/ui/fines_page.py").read_text(encoding="utf-8")
    refusals = (root / "app/ui/refusals_page.py").read_text(encoding="utf-8")
    daily = (root / "app/ui/daily_activity.py").read_text(encoding="utf-8")
    reports = (root / "app/ui/shift_reports.py").read_text(encoding="utf-8")

    assert "ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΠΡΟΣΤΙΜΑ" in fines
    assert "ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ" in fines
    assert "ΑΡΧΕΙΟ ΠΡΑΞΕΩΝ" in fines
    assert "ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΒΑΣ" in refusals
    assert "ΑΡΧΕΙΟ ΒΑΣ" in refusals
    assert "ΤΕΛΕΥΤΑΙΑ ΑΡΝΗΣΗ" in refusals
    assert "ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΗΜΕΡΗΣΙΑ" in daily
    assert 'QPushButton("ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ")' not in daily
    assert "ΣΤΑΤΙΣΤΙΚΑ / ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ" in daily
    assert "ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ" in reports
    assert "ΑΡΧΕΙΟ ΒΑΣ" in reports
    assert "ΟΛΕΣ ΟΙ ΑΝΑΦΟΡΕΣ" in reports
    assert "Διπλό κλικ σε μία γραμμή ανοίγει την αναφορά" in reports


def test_combo_boxes_have_explicit_visible_arrow_assets():
    root = Path(__file__).resolve().parents[1]
    theme = (root / "app/ui/theme.py").read_text(encoding="utf-8")
    spec = (root / "TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    assert "QComboBox::down-arrow" in theme
    assert "combo_arrow_white.svg" in theme
    assert "combo_arrow_dark.svg" in theme
    assert (root / "resources/combo_arrow_white.svg").exists()
    assert (root / "resources/combo_arrow_dark.svg").exists()
    assert "combo_arrow_white.svg" in spec
    assert "combo_arrow_dark.svg" in spec


def test_historical_fine_report_uses_archive_output():
    root = Path(__file__).resolve().parents[1]
    archive_ui = (root / "app/ui/fines_archive.py").read_text(encoding="utf-8")
    assert "generate_shift_report(int(shift_id), archive=True)" in archive_ui
    assert "ΑΝΟΙΓΜΑ ΑΝΑΦΟΡΑΣ ΤΗΣ ΒΑΡΔΙΑΣ" in archive_ui
