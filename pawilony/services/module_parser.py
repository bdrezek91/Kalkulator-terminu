"""
Parser oznaczenia modułu w nazwie pawilonu (projekty wielomodułowe).

Rozpoznaje warianty: "(MODUŁ 1)", "( MODUŁ 1)", "(MODUL 1)", "(1 MODUŁ)",
"MODUŁ 1" bez nawiasów (występuje w rzeczywistym eksporcie) oraz analogiczne
dla modułów 2+, niezależnie od wielkości liter i liczby spacji.

Działanie oparte jest o tokeny (fragmenty rozdzielone białymi znakami), nie
o wyszukiwanie dowolnej cyfry w pobliżu — dzięki temu numer projektu
(np. "18/12/2025") nigdy nie zostaje pomylony z numerem modułu, bo nie jest
samodzielnym tokenem złożonym wyłącznie z 1-2 cyfr.

Jeżeli tekst sugeruje moduł, ale numeru nie da się jednoznacznie rozpoznać
z sąsiedniego tokenu, wynik jest oznaczony jako konflikt zamiast zgadywania.
"""

import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"\S+")
_MODU_TOKEN_RE = re.compile(r"^modu[łl](\d{1,2})?$", re.IGNORECASE)
_DIGIT_TOKEN_RE = re.compile(r"^(\d{1,2})$")


@dataclass
class ModuleParseResult:
    present: bool = False
    number: int | None = None
    conflict: bool = False
    raw_match: str = ""


def _strip_punct(token: str) -> str:
    return token.strip("()[]:,;")


def parse_module(nazwa: str) -> ModuleParseResult:
    if not nazwa:
        return ModuleParseResult(present=False, number=None, conflict=False)

    tokens = _TOKEN_RE.findall(nazwa)
    modu_idx = None
    glued_number = None

    for i, tok in enumerate(tokens):
        stripped = _strip_punct(tok)
        m = _MODU_TOKEN_RE.match(stripped)
        if m:
            modu_idx = i
            if m.group(1):
                glued_number = int(m.group(1))
            break

    if modu_idx is None:
        return ModuleParseResult(present=False, number=None, conflict=False)

    raw_match = " ".join(tokens[max(0, modu_idx - 1): modu_idx + 2])

    if glued_number is not None:
        return ModuleParseResult(present=True, number=glued_number, conflict=False, raw_match=raw_match)

    if modu_idx + 1 < len(tokens):
        after = _DIGIT_TOKEN_RE.match(_strip_punct(tokens[modu_idx + 1]))
        if after:
            return ModuleParseResult(present=True, number=int(after.group(1)), conflict=False, raw_match=raw_match)

    if modu_idx - 1 >= 0:
        before = _DIGIT_TOKEN_RE.match(_strip_punct(tokens[modu_idx - 1]))
        if before:
            return ModuleParseResult(present=True, number=int(before.group(1)), conflict=False, raw_match=raw_match)

    return ModuleParseResult(present=True, number=None, conflict=True, raw_match=raw_match)


def is_counted_module(result: ModuleParseResult) -> bool:
    """Bez oznaczenia modułu ORAZ wyłącznie MODUŁ 1 są wliczane do kalkulacji."""
    if result.conflict:
        return False
    if not result.present:
        return True
    return result.number == 1
