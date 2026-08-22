"""Klasyfikacja statusu procesu pawilonu wg reguł biznesowych."""

from dataclasses import dataclass

from pawilony.services.normalization import NormalizedValue

ACTIVE_STATUSES = ["Logistyka", "Produkcja Zabrze", "Produkcja Czekanów"]
ENDED_STATUSES = [
    "Wysłany do klienta",
    "Wysłany na oddział",
    "Odebrany przez klienta",
    "Odebrany na oddziale",
]

_ACTIVE_LOOKUP = {s.lower(): s for s in ACTIVE_STATUSES}
_ENDED_LOOKUP = {s.lower(): s for s in ENDED_STATUSES}


@dataclass
class StatusResult:
    classification: str  # ACTIVE / ENDED / UNRECOGNIZED / EMPTY / CONFLICT
    canonical: str = ""
    reason: str = ""


def canonicalize_status(value: str) -> str:
    key = value.lower()
    if key in _ACTIVE_LOOKUP:
        return _ACTIVE_LOOKUP[key]
    if key in _ENDED_LOOKUP:
        return _ENDED_LOOKUP[key]
    return value


def classify_status(normalized: NormalizedValue) -> StatusResult:
    if normalized.is_ambiguous:
        canon_values = [canonicalize_status(v) for v in normalized.distinct_values]
        actives = [c for c in canon_values if c in ACTIVE_STATUSES]
        endeds = [c for c in canon_values if c in ENDED_STATUSES]
        if actives and endeds:
            return StatusResult(
                classification="CONFLICT",
                canonical=" / ".join(canon_values),
                reason="status aktywny i zakończony jednocześnie w tym samym rekordzie",
            )
        return StatusResult(
            classification="CONFLICT",
            canonical=" / ".join(canon_values),
            reason="wiele różnych statusów w jednym rekordzie",
        )

    if normalized.value is None:
        return StatusResult(classification="EMPTY", canonical="")

    canon = canonicalize_status(normalized.value)
    if canon in ACTIVE_STATUSES:
        return StatusResult(classification="ACTIVE", canonical=canon)
    if canon in ENDED_STATUSES:
        return StatusResult(classification="ENDED", canonical=canon)
    return StatusResult(
        classification="UNRECOGNIZED",
        canonical=normalized.value,
        reason=f"nierozpoznany status wymagający sklasyfikowania: '{normalized.value}'",
    )
