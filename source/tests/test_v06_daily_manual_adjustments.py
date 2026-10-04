from datetime import datetime
from pathlib import Path

from app.core.db import Database
from app.services.daily_activity import DailyActivityService


def _auto():
    x={f"refusal_{c}":0 for c in "ABCDEFGHI"}
    x.update({
        "h_dka_detected":0,"h_sis_detected":0,"h_both_detected":0,
        "fine_imposition_600":0,"fine_imposition_1200":0,
        "fine_payment_600":0,"fine_payment_1200":0,
        "fine_eparavolo_600":0,"fine_eparavolo_1200":0,
        "fine_detypa_600":0,"fine_detypa_1200":0,
    })
    return x


def test_daily_auto_counts_accept_signed_manual_adjustments(tmp_path: Path):
    db=Database(tmp_path/"db.sqlite3")
    sid=db.start_shift("TEST",datetime(2026,9,26,10,0))
    service=DailyActivityService(db)
    auto=_auto()
    auto["refusal_A"]=5
    auto["fine_imposition_600"]=4
    auto["h_dka_detected"]=3
    service.automatic_summary=lambda shift_id: dict(auto)

    service.save_manual(sid,{
        "adj_refusal_A":1,
        "adj_fine_imposition_600":-1,
        "h_dka_name_change":1,
        "adj_h_dka_only":1,
    })
    s=service.summary_for_shift(sid)
    assert s["refusal_A"]==6
    assert s["fine_imposition_600"]==3
    assert s["h_dka_name_change"]==1
    assert s["h_dka_only"]==3
    assert s["refusal_H"]==4

    # A later automatic act still contributes on top of the saved correction.
    auto["refusal_A"]=6
    assert service.summary_for_shift(sid)["refusal_A"]==7
