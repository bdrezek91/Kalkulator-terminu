import pytest

from pawilony.services.module_parser import is_counted_module, parse_module

VARIANTS_MODULE_1 = [
    "Pawilon 10x2 nr projektu 07/04/2024 (moduł 1)",
    "Pawilon 10x2 nr projektu 07/04/2024 ( moduł 1)",
    "Pawilon 10x2 nr projektu 07/04/2024 (modul 1)",
    "Pawilon 10x2 nr projektu 07/04/2024 (1 moduł)",
    "Pawilon 10x2 nr projektu 07/04/2024 (MODUŁ 1)",
]


@pytest.mark.parametrize("nazwa", VARIANTS_MODULE_1)
def test_module_1_variants_recognized(nazwa):
    result = parse_module(nazwa)
    assert result.present is True
    assert result.number == 1
    assert result.conflict is False
    assert is_counted_module(result) is True


def test_pavilion_without_module_is_counted():
    result = parse_module("Pawilon 6x3 nr projektu 12/06/2024")
    assert result.present is False
    assert is_counted_module(result) is True


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_modules_2_plus_are_skipped(n):
    result = parse_module(f"Pawilon 10x3 nr projektu 12/06/2024 (moduł {n})")
    assert result.number == n
    assert is_counted_module(result) is False


def test_ambiguous_module_mention_is_conflict():
    result = parse_module("Pawilon 10x3 nr projektu 12/06/2024 (moduł)")
    assert result.present is True
    assert result.number is None
    assert result.conflict is True
    assert is_counted_module(result) is False


def test_number_before_word_variant():
    result = parse_module("Pawilon 7x3 nr projektu 17/06/2026 (2 Moduł)")
    assert result.number == 2
    assert result.conflict is False
