"""
Normalizacja surowych wartości komórek z eksportu Optimy.

Zasady (patrz specyfikacja projektu):
- usuwamy spacje na początku/końcu, redukujemy wielokrotne spacje;
- poprawnie obsługujemy znaki nowej linii i artefakt `_x000d_`;
- `null`, pusty tekst i `{pusty}` oznaczają brak wartości;
- powtórzona identyczna wartość (np. "Standard Standard") jest normalizowana
  do jednej wartości i odnotowana jako ostrzeżenie;
- różne wartości w jednej komórce (rozdzielone nową linią) są sygnalizowane
  jako wieloznaczne — wywołujący decyduje, czy to konflikt.
"""

import re
from dataclasses import dataclass, field

_WS_RE = re.compile(r"[ \t]+")
_X000D_RE = re.compile(r"_x000d_", re.IGNORECASE)
EMPTY_MARKERS = {"", "{pusty}", "null", "brak"}


@dataclass
class NormalizedValue:
    """Wynik normalizacji pojedynczej komórki."""

    value: str | None = None  # pojedyncza wartość znormalizowana, None = brak wartości
    is_ambiguous: bool = False  # True, gdy komórka zawiera kilka różnych wartości
    distinct_values: list[str] = field(default_factory=list)  # wypełnione, gdy is_ambiguous
    had_duplicate: bool = False  # True, gdy ta sama wartość powtórzyła się w komórce


def _clean_line(text: str) -> str:
    text = _X000D_RE.sub("\n", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def normalize_cell(raw) -> NormalizedValue:
    """Normalizuje pojedynczą komórkę Excela do postaci użytecznej dla reguł biznesowych."""
    if raw is None:
        return NormalizedValue(value=None)

    text = str(raw)
    text = _X000D_RE.sub("\n", text)
    lines = [_clean_line(line) for line in text.split("\n")]
    lines = [line for line in lines if line != ""]

    distinct: list[str] = []
    distinct_lower_seen: dict[str, str] = {}
    had_duplicate = False
    for line in lines:
        if line.lower() in EMPTY_MARKERS:
            continue
        key = line.lower()
        if key in distinct_lower_seen:
            had_duplicate = True
            continue
        distinct_lower_seen[key] = line
        distinct.append(line)

    if not distinct:
        return NormalizedValue(value=None, had_duplicate=had_duplicate)

    if len(distinct) == 1:
        return NormalizedValue(value=distinct[0], had_duplicate=had_duplicate)

    return NormalizedValue(value=None, is_ambiguous=True, distinct_values=distinct)


def normalize_bool(raw) -> tuple[bool, str | None]:
    """
    Zwraca (wartość_bool, ostrzeżenie_lub_None).

    'Tak' -> True, 'Nie'/pusto/{pusty} -> False.
    Każda inna, nierozpoznana wartość -> False + ostrzeżenie widoczne w raporcie
    (nigdy nie jest cicho traktowana jako zero bez śladu).
    """
    normalized = normalize_cell(raw)
    if normalized.is_ambiguous:
        return False, f"wieloznaczna wartość logiczna: {', '.join(normalized.distinct_values)}"
    if normalized.value is None:
        return False, None
    val = normalized.value.strip().lower()
    if val == "tak":
        return True, None
    if val == "nie":
        return False, None
    return False, f"nierozpoznana wartość logiczna: '{normalized.value}'"
