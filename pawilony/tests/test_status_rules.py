from pawilony.services.normalization import normalize_cell
from pawilony.services.status_rules import classify_status


def test_active_status():
    result = classify_status(normalize_cell("Logistyka"))
    assert result.classification == "ACTIVE"


def test_ended_status():
    result = classify_status(normalize_cell("Wysłany do klienta"))
    assert result.classification == "ENDED"


def test_unrecognized_status():
    result = classify_status(normalize_cell("Zaginiony w transporcie"))
    assert result.classification == "UNRECOGNIZED"


def test_empty_status():
    result = classify_status(normalize_cell(None))
    assert result.classification == "EMPTY"


def test_repeated_identical_status_not_a_conflict():
    result = classify_status(normalize_cell("Logistyka\nLogistyka"))
    assert result.classification == "ACTIVE"


def test_conflict_active_and_ended_mixed():
    result = classify_status(normalize_cell("Produkcja Zabrze\nOdebrany przez klienta"))
    assert result.classification == "CONFLICT"


def test_status_case_insensitive_comparison():
    result = classify_status(normalize_cell("logistyka"))
    assert result.classification == "ACTIVE"
    assert result.canonical == "Logistyka"
