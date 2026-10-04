from __future__ import annotations

import re
import unicodedata

_GREEK_LATIN = str.maketrans({
    "Α":"A","Β":"V","Γ":"G","Δ":"D","Ε":"E","Ζ":"Z","Η":"I","Θ":"TH",
    "Ι":"I","Κ":"K","Λ":"L","Μ":"M","Ν":"N","Ξ":"X","Ο":"O","Π":"P",
    "Ρ":"R","Σ":"S","Τ":"T","Υ":"Y","Φ":"F","Χ":"CH","Ψ":"PS","Ω":"O",
})


def normalize_text(value: str | None) -> str:
    value = (value or "").strip().upper()
    value = "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")
    value = value.translate(_GREEK_LATIN)
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return " ".join(value.split())


def phonetic_key(value: str | None) -> str:
    """Simple language-neutral name key for candidate retrieval.

    This is intentionally conservative. It normalizes Greek/Latin spelling and
    groups common consonant sounds. Final matching is performed by similarity,
    so the original value is always shown to the operator.
    """
    s = normalize_text(value).replace(" ", "")
    if not s:
        return ""
    replacements = (
        ("TH", "T"), ("PH", "F"), ("CH", "H"), ("SH", "S"), ("TS", "C"),
        ("TZ", "J"), ("CK", "K"), ("QU", "K"), ("W", "V"), ("Y", "I"),
    )
    for a, b in replacements:
        s = s.replace(a, b)
    first = s[0]
    body = re.sub(r"[AEIOUY]", "", s[1:])
    body = re.sub(r"(.)\1+", r"\1", body)
    groups = str.maketrans({"B":"P","D":"T","G":"K","C":"K","J":"Z","V":"F"})
    body = body.translate(groups)
    return (first + body)[:12]


def normalize_birth_date(value: str | None) -> str | None:
    from datetime import datetime
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw
