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
    indices = {key: [] for key in _ALIASES}
    unknown = False
    for offset, row in enumerate(rows):
        category = payment_category(row.get("payment_type"))
        if category is None:
            unknown = True
        else:
            indices[category].append(f"C{first_row + offset}")
    return {key: "=SUM(" + ",".join(cells) + ")" if cells else "=0"
            for key, cells in indices.items()}, unknown
