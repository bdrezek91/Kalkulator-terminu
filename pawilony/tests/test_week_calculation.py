from datetime import date
from decimal import Decimal

from pawilony.services.hours import HoursResult
from pawilony.services.week_calculation import BacklogTotals, calculate_earliest_week, next_planning_monday


def test_effective_general_capacity_not_prematurely_rounded(active_config):
    assert active_config.effective_general_capacity == Decimal("45") * Decimal("0.85")
    assert active_config.effective_general_capacity == Decimal("38.25")


def test_buffer_15_percent_applied_to_hydraulic_capacity(active_config):
    assert active_config.effective_hydraulic_capacity_hours == Decimal("8") * Decimal("40") * Decimal("0.85")
    assert active_config.effective_hydraulic_capacity_hours == Decimal("272.00")


def test_next_planning_monday_from_monday_is_today():
    monday = date(2026, 8, 17)  # poniedziałek
    assert monday.weekday() == 0
    assert next_planning_monday(monday) == monday


def test_next_planning_monday_from_midweek_is_next_monday():
    wednesday = date(2026, 8, 19)
    result = next_planning_monday(wednesday)
    assert result.weekday() == 0
    assert result == date(2026, 8, 24)


def test_base_capacity_bottleneck(active_config):
    backlog = BacklogTotals(base_units=0, hydraulic_hours=Decimal("0"), welding_hours=Decimal("0"), fibo_wood_hours=Decimal("0"))
    new_pavilion = HoursResult()  # brak wyposażenia specjalistycznego
    result = calculate_earliest_week(backlog, new_pavilion, active_config, today=date(2026, 8, 17))
    assert result.result_weeks == 1
    assert result.bottleneck_key == "base"


def test_fibo_wood_bottleneck(active_config):
    # duży backlog FIBO/boazeria wymusza więcej tygodni niż baza
    backlog = BacklogTotals(
        base_units=1,
        hydraulic_hours=Decimal("0"),
        welding_hours=Decimal("0"),
        fibo_wood_hours=Decimal("500"),
    )
    new_pavilion = HoursResult(fibo_wood_hours=Decimal("50"))
    result = calculate_earliest_week(backlog, new_pavilion, active_config, today=date(2026, 8, 17))
    assert result.bottleneck_key == "fibo_wood"
    # (500+50)/102 = 5.39 -> ceil = 6
    assert result.result_weeks == 6


def test_brigade_not_required_has_zero_weeks(active_config):
    backlog = BacklogTotals(base_units=0, hydraulic_hours=Decimal("1000"), welding_hours=Decimal("0"), fibo_wood_hours=Decimal("0"))
    new_pavilion = HoursResult(hydraulic_hours=Decimal("0"))  # nowy pawilon nie wymaga hydraulika
    result = calculate_earliest_week(backlog, new_pavilion, active_config, today=date(2026, 8, 17))
    hydraulic_outcome = next(o for o in result.brigade_outcomes if o.key == "hydraulic")
    assert hydraulic_outcome.required is False
    assert hydraulic_outcome.weeks == 0


def test_iso_week_year_boundary(active_config):
    # Startujemy tuż przed przełomem roku, wymuszamy dużo tygodni żeby przejść na kolejny rok
    backlog = BacklogTotals(base_units=0, hydraulic_hours=Decimal("0"), welding_hours=Decimal("0"), fibo_wood_hours=Decimal("0"))
    new_pavilion = HoursResult()
    result = calculate_earliest_week(backlog, new_pavilion, active_config, today=date(2025, 12, 29))
    # 2025-12-29 to poniedziałek; wynik week=1 -> ten sam tydzień
    assert result.week_start == date(2025, 12, 29)
    iso_year, iso_week, _ = result.week_start.isocalendar()
    assert result.iso_year == iso_year
    assert result.iso_week == iso_week


def test_result_is_max_across_all_required_brigades(active_config):
    # Baza wymaga 1 tygodnia, hydraulicy 2, spawacze 3, FIBO/boazeria 1 -> wynik = 3 (spawacze).
    backlog = BacklogTotals(
        base_units=0,
        hydraulic_hours=Decimal("0"),
        welding_hours=Decimal("500"),
        fibo_wood_hours=Decimal("0"),
    )
    new_pavilion = HoursResult(
        hydraulic_hours=Decimal("100"),
        welding_hours=Decimal("50"),
        fibo_wood_hours=Decimal("10"),
    )
    result = calculate_earliest_week(backlog, new_pavilion, active_config, today=date(2026, 8, 17))
    assert result.bottleneck_key == "welding"
    welding_outcome = next(o for o in result.brigade_outcomes if o.key == "welding")
    assert result.result_weeks == welding_outcome.weeks
    assert result.result_weeks == max(o.weeks for o in result.brigade_outcomes)
