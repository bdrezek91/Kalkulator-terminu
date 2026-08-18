from decimal import Decimal

from pawilony.services.hours import PavilionEquipment, calculate_hours


def test_kuchnia_standard(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Standard"))
    assert result.hydraulic_hours == Decimal("10")


def test_kuchnia_lux(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux"))
    assert result.hydraulic_hours == Decimal("10")


def test_toaleta_variants(operation_times):
    assert calculate_hours(PavilionEquipment(toaleta="Standard")).hydraulic_hours == Decimal("7")
    assert calculate_hours(PavilionEquipment(toaleta="Komfort")).hydraulic_hours == Decimal("12")
    assert calculate_hours(PavilionEquipment(toaleta="Premium")).hydraulic_hours == Decimal("10")


def test_toaleta_custom_wc_variants(operation_times):
    # Niestandardowe warianty WC mają własną pulę mocy — liczą się jako
    # custom_bathroom_hours, nie hydraulic_hours.
    assert calculate_hours(PavilionEquipment(toaleta="Fibo")).custom_bathroom_hours == Decimal("80")
    assert calculate_hours(PavilionEquipment(toaleta="Fibo")).hydraulic_hours == Decimal("0")
    assert calculate_hours(PavilionEquipment(toaleta="Premium płytki")).custom_bathroom_hours == Decimal("100")
    assert calculate_hours(PavilionEquipment(toaleta="Premium + boazeria")).custom_bathroom_hours == Decimal("150")


def test_lazienka_replaces_toaleta_and_prysznic(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Standard", toaleta="Premium", prysznic=True))
    # tylko łazienka się liczy — 7h, nie 7+10+8
    assert result.hydraulic_hours == Decimal("7")


def test_kuchnia_sums_with_lazienka(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", lazienka="Premium"))
    assert result.hydraulic_hours == Decimal("10") + Decimal("10")


def test_statyka_sums_with_kratownica(operation_times):
    # Mechanika czystego liczenia godzin — sumuje, gdyby oba flagi trafiły tutaj.
    # W praktyce ta kombinacja jest zablokowana wcześniej (formularz/import), bo
    # pełna konstrukcja/statyka i kratownica wykluczają się biznesowo.
    result = calculate_hours(PavilionEquipment(pelna_statyka=True, kratownica=True))
    assert result.welding_hours == Decimal("12") + Decimal("4")


def test_fibo_sums_with_boazeria(operation_times):
    result = calculate_hours(PavilionEquipment(fibo=True, boazeria=True))
    assert result.fibo_wood_hours == Decimal("50") + Decimal("70")


def test_brigades_are_independent_not_summed_together(operation_times):
    result = calculate_hours(
        PavilionEquipment(kuchnia="Lux", pelna_statyka=True, fibo=True)
    )
    assert result.hydraulic_hours == Decimal("10")
    assert result.welding_hours == Decimal("12")
    assert result.fibo_wood_hours == Decimal("50")
    # brygady nie sumują się w jeden ciąg — sprawdzamy, że są przechowywane osobno
    assert result.hydraulic_hours + result.welding_hours + result.fibo_wood_hours == Decimal("72")


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
