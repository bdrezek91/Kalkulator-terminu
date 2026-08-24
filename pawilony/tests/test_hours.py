from decimal import Decimal

from pawilony.services.hours import PavilionEquipment, calculate_hours


def test_kuchnia_standard(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Standard"))
    assert result.hydraulic_hours == Decimal("10")


def test_kuchnia_lux(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux"))
    assert result.hydraulic_hours == Decimal("10")


def test_toaleta_variants(operation_times):
    # Komfort/Premium mają już wliczone godziny Fibo/Płytki (nie są to osobne
    # dodatki), podzielone 40% hydraulika / 60% brygada FIBO/boazeria.
    # Toaleta = połowa odpowiadającego wariantu Łazienki w obu składowych:
    # Standard 7h (bez podziału); Komfort 18h hydraulika + 27h FIBO/boazeria;
    # Premium 20h hydraulika + 30h FIBO/boazeria.
    standard = calculate_hours(PavilionEquipment(toaleta="Standard"))
    assert standard.hydraulic_hours == Decimal("7")
    assert standard.fibo_wood_hours == Decimal("0")

    komfort = calculate_hours(PavilionEquipment(toaleta="Komfort"))
    assert komfort.hydraulic_hours == Decimal("18")
    assert komfort.fibo_wood_hours == Decimal("27")

    premium = calculate_hours(PavilionEquipment(toaleta="Premium"))
    assert premium.hydraulic_hours == Decimal("20")
    assert premium.fibo_wood_hours == Decimal("30")


def test_kuchnia_count_multiplies_hours(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", kuchnia_count=3))
    assert result.hydraulic_hours == Decimal("10") * 3


def test_default_kuchnia_count_is_one(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux"))
    assert result.hydraulic_hours == Decimal("10")


def test_bathroom_count_multiplies_toaleta_hours_including_fibo_split(operation_times):
    result = calculate_hours(PavilionEquipment(toaleta="Komfort", bathroom_count=2))
    assert result.hydraulic_hours == Decimal("18") * 2
    assert result.fibo_wood_hours == Decimal("27") * 2


def test_bathroom_count_multiplies_lazienka_hours_including_fibo_split(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Premium", bathroom_count=2))
    assert result.hydraulic_hours == Decimal("40") * 2
    assert result.fibo_wood_hours == Decimal("60") * 2


def test_bathroom_count_multiplies_prysznic(operation_times):
    result = calculate_hours(PavilionEquipment(prysznic=True, bathroom_count=3))
    assert result.hydraulic_hours == Decimal("8") * 3


def test_default_bathroom_count_is_one(operation_times):
    result = calculate_hours(PavilionEquipment(toaleta="Standard"))
    assert result.hydraulic_hours == Decimal("7")


def test_lazienka_replaces_toaleta_and_prysznic(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Standard", toaleta="Premium", prysznic=True))
    # tylko łazienka się liczy — 7h, nie 7+55+8
    assert result.hydraulic_hours == Decimal("7")


def test_kuchnia_sums_with_lazienka(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", lazienka="Premium"))
    assert result.hydraulic_hours == Decimal("10") + Decimal("40")
    assert result.fibo_wood_hours == Decimal("60")


def test_statyka_sums_with_kratownica(operation_times):
    # Mechanika czystego liczenia godzin — sumuje, gdyby oba flagi trafiły tutaj.
    # W praktyce ta kombinacja jest zablokowana wcześniej (formularz/import), bo
    # pełna konstrukcja/statyka i kratownica wykluczają się biznesowo.
    result = calculate_hours(PavilionEquipment(pelna_statyka=True, kratownica=True))
    assert result.welding_hours == Decimal("12") + Decimal("4")


def test_brigades_are_independent_not_summed_together(operation_times):
    result = calculate_hours(
        PavilionEquipment(kuchnia="Lux", pelna_statyka=True, toaleta="Komfort")
    )
    assert result.hydraulic_hours == Decimal("10") + Decimal("18")
    assert result.welding_hours == Decimal("12")
    assert result.fibo_wood_hours == Decimal("27")
    # brygady nie sumują się w jeden ciąg — sprawdzamy, że są przechowywane osobno
    assert result.hydraulic_hours + result.welding_hours + result.fibo_wood_hours == Decimal("67")


def test_informational_fields_do_not_affect_brigade_hours(operation_times):
    result = calculate_hours(
        PavilionEquipment(stolarka_nst=True, zaluzje_fasadowe=True, rolety=True)
    )
    assert result.hydraulic_hours == Decimal("0")
    assert result.welding_hours == Decimal("0")
    assert result.fibo_wood_hours == Decimal("0")
    assert result.informational_hours == Decimal("15")


def test_no_equipment_is_not_custom(operation_times):
    result = calculate_hours(PavilionEquipment())
    assert result.is_custom is False


def test_any_brigade_hours_marks_custom(operation_times):
    result = calculate_hours(PavilionEquipment(kratownica=True))
    assert result.is_custom is True


def test_statyka_and_kratownica_multiplied_by_module_count(operation_times):
    # Projekt wielomodułowy — każdy moduł wymaga własnej konstrukcji spawanej.
    result = calculate_hours(PavilionEquipment(pelna_statyka=True, module_count=3))
    assert result.welding_hours == Decimal("12") * 3


def test_kratownica_multiplied_by_module_count(operation_times):
    result = calculate_hours(PavilionEquipment(kratownica=True, module_count=2))
    assert result.welding_hours == Decimal("4") * 2


def test_module_count_does_not_affect_other_brigades(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", toaleta="Komfort", module_count=3))
    assert result.hydraulic_hours == Decimal("10") + Decimal("18")
    assert result.fibo_wood_hours == Decimal("27")


def test_default_module_count_is_one(operation_times):
    result = calculate_hours(PavilionEquipment(pelna_statyka=True))
    assert result.welding_hours == Decimal("12")


def test_lazienka_komfort_splits_fibo_plytki_hours_40_60(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Komfort"))
    assert result.hydraulic_hours == Decimal("36")
    assert result.fibo_wood_hours == Decimal("54")
    assert result.hydraulic_hours + result.fibo_wood_hours == Decimal("90")


def test_lazienka_premium_splits_fibo_plytki_hours_40_60(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Premium"))
    assert result.hydraulic_hours == Decimal("40")
    assert result.fibo_wood_hours == Decimal("60")
    assert result.hydraulic_hours + result.fibo_wood_hours == Decimal("100")


def test_toaleta_komfort_premium_take_half_the_time_of_lazienka(operation_times):
    lazienka_komfort = calculate_hours(PavilionEquipment(lazienka="Komfort"))
    toaleta_komfort = calculate_hours(PavilionEquipment(toaleta="Komfort"))
    assert toaleta_komfort.hydraulic_hours == lazienka_komfort.hydraulic_hours / 2
    assert toaleta_komfort.fibo_wood_hours == lazienka_komfort.fibo_wood_hours / 2

    lazienka_premium = calculate_hours(PavilionEquipment(lazienka="Premium"))
    toaleta_premium = calculate_hours(PavilionEquipment(toaleta="Premium"))
    assert toaleta_premium.hydraulic_hours == lazienka_premium.hydraulic_hours / 2
    assert toaleta_premium.fibo_wood_hours == lazienka_premium.fibo_wood_hours / 2


def test_lazienka_standard_and_toaleta_standard_have_no_fibo_split(operation_times):
    assert calculate_hours(PavilionEquipment(lazienka="Standard")).fibo_wood_hours == Decimal("0")
    assert calculate_hours(PavilionEquipment(toaleta="Standard")).fibo_wood_hours == Decimal("0")
