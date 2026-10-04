from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def clean(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split())


def parse_greek_date(value: Any) -> date | None:
    """Mirror VBA date parsing: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, 2-digit year."""
    if value is None or clean(value) == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = clean(value).replace("-", "/").replace(".", "/")
    parts = s.split("/")
    if len(parts) != 3 or not all(p.strip().isdigit() for p in parts):
        raise ValueError(f"Μη έγκυρη ημερομηνία: {value}")
    d, m, y = map(int, parts)
    if y < 100:
        y += 2000 if y <= 29 else 1900
    try:
        return date(y, m, d)
    except ValueError as exc:
        raise ValueError(f"Μη έγκυρη ημερομηνία: {value}") from exc


def fmt_date(value: Any, sep: str = "/") -> str:
    d = parse_greek_date(value)
    return "" if d is None else d.strftime(f"%d{sep}%m{sep}%Y")


def operational_date(now: datetime, cutoff_hour: int = 10) -> date:
    return now.date() if now.hour >= cutoff_hour else now.date() - timedelta(days=1)


def duty_range(op_date: date) -> tuple[date, date]:
    return op_date, op_date + timedelta(days=1)


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", clean(value)).strip(" .") or "ΧΩΡΙΣ_ΟΝΟΜΑ"


GREEK_MONTHS = {
    1: "ΙΑΝΟΥΑΡΙΟΣ", 2: "ΦΕΒΡΟΥΑΡΙΟΣ", 3: "ΜΑΡΤΙΟΣ", 4: "ΑΠΡΙΛΙΟΣ",
    5: "ΜΑΙΟΣ", 6: "ΙΟΥΝΙΟΣ", 7: "ΙΟΥΛΙΟΣ", 8: "ΑΥΓΟΥΣΤΟΣ",
    9: "ΣΕΠΤΕΜΒΡΙΟΣ", 10: "ΟΚΤΩΒΡΙΟΣ", 11: "ΝΟΕΜΒΡΙΟΣ", 12: "ΔΕΚΕΜΒΡΙΟΣ",
}
