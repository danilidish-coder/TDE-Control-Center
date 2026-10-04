from pathlib import Path


def test_daily_activity_action_labels():
    root = Path(__file__).resolve().parents[1]
    page = (root / "app/ui/daily_activity.py").read_text(encoding="utf-8")
    assert "ΠΡΟΒΟΛΗ - ΕΚΤΥΠΩΣΗ ΤΡΕΧΟΥΣΑΣ ΑΝΑΦΟΡΑΣ" in page
    assert "ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ" in page
    assert "ΑΝΑΦΟΡΑ ΤΡΕΧΟΥΣΑΣ ΒΑΡΔΙΑΣ · ΗΜΕΡΗΣΙΑ" not in page
    assert "ΣΤΑΤΙΣΤΙΚΑ / ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ" not in page
