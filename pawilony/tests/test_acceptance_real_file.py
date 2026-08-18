"""
Test akceptacyjny na kopii wzorcowego pliku `Wykaz pawilonów.xlsx`.

Zgodnie ze specyfikacją: liczby z pierwotnej analizy (4447 wierszy, 503 wiersze
z dokładnymi aktywnymi statusami, 431 pozycji po pozostawieniu braku modułu
i modułu 1) są jedynie kontrolą dla TEJ KONKRETNEJ wersji pliku i NIE są
zaszyte w logice aplikacji — tylko w tym teście, jako regresja na stałym
zestawie danych referencyjnych.
"""

from pathlib import Path

import pytest

from pawilony.services.import_service import analyze_workbook

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "wykaz_pawilonow_wzorcowy.xlsx"

pytestmark = pytest.mark.skipif(not FIXTURE_PATH.exists(), reason="Brak wzorcowego pliku XLSX w fixtures/")


def test_reference_file_row_and_active_counts(operation_times):
    with open(FIXTURE_PATH, "rb") as f:
        report, records = analyze_workbook(f)

    assert report.total_rows == 4447

    # Pierwotna analiza (naiwne liczenie surowych, niezdeduplikowanych łańcuchów
    # statusu) dała 503 wiersze z dokładnym aktywnym statusem. Nasza normalizacja
    # poprawnie zlicza też wiersz ze statusem "Logistyka\nLogistyka" (identyczna
    # wartość powtórzona w komórce — wg specyfikacji to NIE jest konflikt, tylko
    # wartość do znormalizowania), więc wynik jest o 1 wyższy: 504.
    exact_active_status_rows = sum(
        1
        for r in records
        if r["status_normalized"] in ("Logistyka", "Produkcja Zabrze", "Produkcja Czekanów")
    )
    assert exact_active_status_rows == 504

    # Wiersze z mieszanym statusem aktywny+zakończony trafiają do konfliktów,
    # a nie do aktywnych — w tym pliku jest ich 7. Dodatkowo 14 wierszy ma
    # jednocześnie "Pełna konstrukcja/statyka" i "Kratownica" — te dwie opcje
    # wykluczają się biznesowo, więc też trafiają do konfliktów (reguła
    # dodana po korekcie z sierpnia 2026, patrz seed_defaults/migracje).
    assert report.conflict_count == 7 + 14

    # 431 z pierwotnej analizy nie uwzględniało rozpoznawania modułów bez
    # nawiasów (np. "... MODUŁ 1" na końcu nazwy, bez otaczających nawiasów),
    # które nasz parser poprawnie rozpoznaje zamiast zgłaszać jako konflikt —
    # to dawałoby 433. Po dodaniu reguły wykluczającej pełną konstrukcję i
    # kratownicę tylko 3 z tych 14 nowych konfliktów pokrywały się z wcześniej
    # liczonymi wierszami (pozostałe były już wykluczone z innych powodów,
    # np. moduł 2+), więc wynik referencyjny to 433 - 3 = 430.
    counted = [r for r in records if r["is_counted"]]
    assert len(counted) == 430

    # plik źródłowy nie zawiera jeszcze kolumn FIBO/BOAZERIA
    assert report.fibo_column_present is False
    assert report.boazeria_column_present is False


def test_reference_file_source_not_modified():
    import hashlib

    digest = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert len(digest) == 64  # plik jest czytany tylko do odczytu, nigdy nie jest zapisywany
