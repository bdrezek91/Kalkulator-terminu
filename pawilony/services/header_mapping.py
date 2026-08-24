"""
Centralna mapa aliasów nagłówków kolumn eksportu Optimy.

Nagłówki nie są dopasowywane po numerze prefiksu atrybutu (numery mogą się
zmienić), tylko po fragmencie tekstu, bez uwzględniania wielkości liter.
"""

import re
import unicodedata

# canonical_field -> lista fragmentów tekstu, których obecność w znormalizowanym
# nagłówku jednoznacznie identyfikuje kolumnę. Kolejność ma znaczenie —
# pierwszy pasujący fragment wygrywa.
HEADER_ALIASES: dict[str, list[str]] = {
    "kod": ["KOD"],
    "nazwa": ["NAZWA"],
    "typ": ["TYP"],
    "stan_zasobow": ["STAN ZASOBOW", "STAN ZASOBÓW"],
    "ilosc_dostepna": ["ILOSC DOSTEPNA", "ILOŚĆ DOSTĘPNA"],
    "jm": ["JM"],
    "oddzial": ["ODDZIAL", "ODDZIAŁ"],
    "rodzaj": ["RODZAJ"],
    "status_proces": ["STATUS PROCESU", "STATUS PROCES"],
    "termin_realiz": ["TERMIN REALIZ"],
    "plyty_niestandard": ["PLYTY NIESTANDAR", "PŁYTY NIESTANDAR"],
    "pelna_statyka": ["PELNA", "STATYKA", "PEŁNA"],
    "kratownica": ["KRATOWNICA"],
    "kuchnia": ["KUCHNIA"],
    "prysznic": ["PRYSZNIC"],
    "toaleta": ["TOALETA"],
    "stolarka_nst": ["STOLARKA NST", "STOLARKA"],
    "zaluzje_fasadowe": ["ZALUZJE", "ŻALUZJE"],
    "rolety": ["ROLETY"],
    "lazienka": ["LAZIENKA", "ŁAZIENKA"],
    "inne_niestandard": ["INNE NIESTANDARD"],
}

REQUIRED_FIELDS = ["kod", "nazwa", "typ", "stan_zasobow", "status_proces"]

_PREFIX_RE = re.compile(r"^\s*\d+\s*[\.\)]\s*")
_ATTR_SUFFIX_RE = re.compile(r"\(\s*atrybut\s*\)\s*$", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_header(header: str) -> str:
    if header is None:
        return ""
    text = str(header)
    text = _PREFIX_RE.sub("", text)
    text = _ATTR_SUFFIX_RE.sub("", text)
    text = text.strip().upper()
    text = _strip_accents(text)
    return text


def build_header_map(header_row: list) -> tuple[dict[str, int], list[str], list[str]]:
    """
    Zwraca (mapa pole->indeks_kolumny, brakujące_wymagane_pola, nierozpoznane_nagłówki).
    """
    normalized_headers = [normalize_header(h) for h in header_row]

    field_map: dict[str, int] = {}
    matched_columns: set[int] = set()

    for field_name, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            alias_norm = _strip_accents(alias.upper())
            for idx, norm_header in enumerate(normalized_headers):
                if idx in matched_columns:
                    continue
                if alias_norm in norm_header:
                    field_map[field_name] = idx
                    matched_columns.add(idx)
                    break
            if field_name in field_map:
                break

    missing_required = [f for f in REQUIRED_FIELDS if f not in field_map]
    unrecognized_headers = [
        str(header_row[idx]) for idx in range(len(header_row)) if idx not in matched_columns and header_row[idx]
    ]
    return field_map, missing_required, unrecognized_headers
