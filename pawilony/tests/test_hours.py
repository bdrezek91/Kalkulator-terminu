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
    # dodatki): Toaleta Standard 7h, Komfort 12+40=52h, Premium 10+45=55h.
    assert calculate_hours(PavilionEquipment(toaleta="Standard")).hydraulic_hours == Decimal("7")
    assert calculate_hours(PavilionEquipment(toaleta="Komfort")).hydraulic_hours == Decimal("52")
    assert calculate_hours(PavilionEquipment(toaleta="Premium")).hydraulic_hours == Decimal("55")


def test_wc_addon_boazeria_is_independent_of_toaleta_variant(operation_times):
    # Dodatek Boazeria ma własną pulę mocy (custom_bathroom_hours) i dolicza
    # się NIEZALEŻNIE od wybranego wariantu Toalety/Łazienki.
    result = calculate_hours(PavilionEquipment(toaleta="Standard", wc_addon_boazeria=True))
    assert result.hydraulic_hours == Decimal("7")
    assert result.custom_bathroom_hours == Decimal("150")


def test_wc_addon_boazeria_works_with_lazienka_too(operation_times):
    # Dodatek działa zarówno przy Toalecie, jak i przy Łazience.
    result = calculate_hours(PavilionEquipment(lazienka="Premium", wc_addon_boazeria=True))
    assert result.hydraulic_hours == Decimal("100")
    assert result.custom_bathroom_hours == Decimal("150")


def test_wc_addon_boazeria_without_any_toaleta_or_lazienka(operation_times):
    # Dodatek sam w sobie, bez wybranej toalety/łazienki, wciąż się liczy.
    result = calculate_hours(PavilionEquipment(wc_addon_boazeria=True))
    assert result.hydraulic_hours == Decimal("0")
    assert result.custom_bathroom_hours == Decimal("150")


def test_lazienka_replaces_toaleta_and_prysznic(operation_times):
    result = calculate_hours(PavilionEquipment(lazienka="Standard", toaleta="Premium", prysznic=True))
    # tylko łazienka się liczy — 7h, nie 7+55+8
    assert result.hydraulic_hours == Decimal("7")


def test_kuchnia_sums_with_lazienka(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", lazienka="Premium"))
    assert result.hydraulic_hours == Decimal("10") + Decimal("100")


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


def test_statyka_and_kratownica_multiplied_by_module_count(operation_times):
    # Projekt wielomodułowy — każdy moduł wymaga własnej konstrukcji spawanej.
    result = calculate_hours(PavilionEquipment(pelna_statyka=True, module_count=3))
    assert result.welding_hours == Decimal("12") * 3


def test_kratownica_multiplied_by_module_count(operation_times):
    result = calculate_hours(PavilionEquipment(kratownica=True, module_count=2))
    assert result.welding_hours == Decimal("4") * 2


def test_module_count_does_not_affect_other_brigades(operation_times):
    result = calculate_hours(PavilionEquipment(kuchnia="Lux", fibo=True, module_count=3))
    assert result.hydraulic_hours == Decimal("10")
    assert result.fibo_wood_hours == Decimal("50")


def test_default_module_count_is_one(operation_times):
    result = calculate_hours(PavilionEquipment(pelna_statyka=True))
    assert result.welding_hours == Decimal("12")
