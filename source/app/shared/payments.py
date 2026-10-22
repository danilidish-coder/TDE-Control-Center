"""Explicit settlement classification shared by reports; unknown values stay unknown."""
from app.core.textnorm import normalize_text

_ALIASES = {
    "payment": ("ΧΡΗΜ ΠΟΣΟ", "ΧΡΗΜΑΤΙΚΟ ΠΟΣΟ", "ΜΕΤΡΗΤΑ", "CASH"),
    "eparavolo": ("e-ΠΑΡΑΒΟΛΟ", "eΠαράβολο", "ePARAVOLO"),
    "detypa": ("ΕΦΟΡΙΑ", "Δ.Ε. ΤΥΠΟΥ-Α", "DE TYPOU A", "DE TYPE A"),
}
_METHODS = {normalize_text(alias).replace(" ", ""): kind
            for kind, aliases in _ALIASES.items() for alias in aliases}


def payment_category(method: str | None) -> str | None:
    return _METHODS.get(normalize_text(method).replace(" ", ""))


def protocol_category_formulas(rows, first_row: int) -> tuple[dict[str, str], bool]:
    """Keep live amount formulas, raw settlement fields, and the existing columns."""
    rows = list(rows)
    last_row = max(first_row, first_row + len(rows) - 1)
    # A hidden metadata column keeps formulas bounded for large lists. It does
    # not add a financial field or alter any of the six printed columns.
    formulas = {kind: f'=SUMIF(G{first_row}:G{last_row},"{kind}",C{first_row}:C{last_row})'
                for kind in _ALIASES}
    return formulas, any(payment_category(row.get("payment_type")) is None for row in rows)
