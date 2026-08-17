from pawilony.services.normalization import normalize_bool, normalize_cell


def test_empty_and_pusty_are_none():
    assert normalize_cell(None).value is None
    assert normalize_cell("").value is None
    assert normalize_cell("{pusty}").value is None
    assert normalize_cell("  {pusty}  ").value is None


def test_strip_and_collapse_whitespace():
    # spacje wewnątrz jednej linii są redukowane, ale to wciąż jedna wartość
    assert normalize_cell("  Standard   Lux  ").value == "Standard Lux"
    assert normalize_cell("  Standard  ").value == "Standard"


def test_x000d_and_newline_handling():
    result = normalize_cell("Logistyka_x000d_\nLogistyka")
    assert result.value == "Logistyka"
    assert result.had_duplicate is True


def test_duplicate_identical_value_is_normalized_with_flag():
    result = normalize_cell("Standard\nStandard")
    assert result.value == "Standard"
    assert result.had_duplicate is True


def test_case_insensitive_duplicate_detection():
    result = normalize_cell("Logistyka\nlogistyka")
    assert result.value == "Logistyka"
    assert result.had_duplicate is True


def test_ambiguous_multi_distinct_values():
    result = normalize_cell("Odebrany przez klienta\nLogistyka")
    assert result.is_ambiguous is True
    assert result.value is None
    assert set(result.distinct_values) == {"Odebrany przez klienta", "Logistyka"}


def test_normalize_bool():
    assert normalize_bool("Tak") == (True, None)
    assert normalize_bool("Nie") == (False, None)
    assert normalize_bool(None) == (False, None)
    assert normalize_bool("{pusty}") == (False, None)
    val, warn = normalize_bool("Może")
    assert val is False
    assert warn is not None
