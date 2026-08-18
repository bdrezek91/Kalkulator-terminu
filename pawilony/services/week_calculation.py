"""
Algorytm wyznaczania najwcześniejszego bezpiecznego tygodnia realizacji.

Ograniczeniem terminu jest wyłącznie obciążenie brygad wykończeniowych
(hydraulika, spawacze, FIBO/boazeria) — moc samej produkcji pawilonów
("produkcja ogólna") jest pokazywana wyłącznie informacyjnie i NIE wpływa
na wynik, bo firma ma jej pod dostatkiem; wąskim gardłem jest wyposażenie.

Obliczenia pojemności wykonywane są na typie Decimal (nigdy float), a
zaokrąglenie w górę następuje dopiero na etapie liczby wymaganych tygodni.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from pawilony.models import CapacityConfiguration
from pawilony.services.hours import HoursResult

BASE_LABEL = "Produkcja ogólna"
BRIGADE_LABELS = {
    "hydraulic": "Hydraulicy",
    "welding": "Spawacze",
    "fibo_wood": "FIBO/boazeria",
    "custom_bathroom": "Niestandardowe łazienki",
}


@dataclass
class BacklogTotals:
    base_units: int = 0
    hydraulic_hours: Decimal = Decimal("0")
    welding_hours: Decimal = Decimal("0")
    fibo_wood_hours: Decimal = Decimal("0")
    custom_bathroom_hours: Decimal = Decimal("0")


@dataclass
class BrigadeOutcome:
    key: str
    weeks: int
    current_backlog: Decimal
    effective_capacity: Decimal
    required: bool


@dataclass
class WeekResult:
    result_weeks: int
    iso_week: int
    iso_year: int
    week_start: date
    week_end: date
    bottleneck_key: str | None  # None = żadna brygada wykończeniowa nie jest wymagana
    brigade_outcomes: list[BrigadeOutcome] = field(default_factory=list)
    base_outcome: BrigadeOutcome | None = None  # informacyjnie, nie wpływa na wynik


def _ceil_decimal_to_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def next_planning_monday(today: date | None = None) -> date:
    """
    Najbliższy 'pełny' poniedziałek: jeśli dziś jest poniedziałek, to dziś
    (cały tydzień jest dostępny). W przeciwnym razie kolejny poniedziałek —
    nie zakładamy dostępności w części bieżącego tygodnia.
    """
    today = today or date.today()
    weekday = today.weekday()  # Monday = 0
    if weekday == 0:
        return today
    return today + timedelta(days=(7 - weekday))


def calculate_earliest_week(
    backlog: BacklogTotals,
    new_pavilion_hours: HoursResult,
    config: CapacityConfiguration,
    today: date | None = None,
) -> WeekResult:
    start_monday = next_planning_monday(today)

    base_weeks = _ceil_decimal_to_int(
        (Decimal(backlog.base_units + 1)) / config.effective_general_capacity
    )
    base_outcome = BrigadeOutcome(
        key="base",
        weeks=base_weeks,
        current_backlog=Decimal(backlog.base_units),
        effective_capacity=config.effective_general_capacity,
        required=True,
    )

    def brigade_weeks(key: str, backlog_hours: Decimal, new_hours: Decimal, capacity: Decimal) -> BrigadeOutcome:
        required = new_hours > 0
        if not required:
            weeks = 0
        else:
            weeks = _ceil_decimal_to_int((backlog_hours + new_hours) / capacity)
        return BrigadeOutcome(
            key=key,
            weeks=weeks,
            current_backlog=backlog_hours,
            effective_capacity=capacity,
            required=required,
        )

    outcomes: list[BrigadeOutcome] = [
        brigade_weeks(
            "hydraulic",
            backlog.hydraulic_hours,
            new_pavilion_hours.hydraulic_hours,
            config.effective_hydraulic_capacity_hours,
        ),
        brigade_weeks(
            "welding",
            backlog.welding_hours,
            new_pavilion_hours.welding_hours,
            config.effective_welding_capacity_hours,
        ),
        brigade_weeks(
            "fibo_wood",
            backlog.fibo_wood_hours,
            new_pavilion_hours.fibo_wood_hours,
            config.effective_fibo_wood_capacity_hours,
        ),
        brigade_weeks(
            "custom_bathroom",
            backlog.custom_bathroom_hours,
            new_pavilion_hours.custom_bathroom_hours,
            config.effective_custom_bathroom_capacity_hours,
        ),
    ]

    # Wynik zależy WYŁĄCZNIE od brygad wykończeniowych — produkcja ogólna
    # (base_outcome) jest tylko informacyjna i celowo pomijana tutaj.
    result_weeks = max(1, *(o.weeks for o in outcomes))
    required_outcomes = [o for o in outcomes if o.required]
    bottleneck = max(required_outcomes, key=lambda o: o.weeks).key if required_outcomes else None

    target_monday = start_monday + timedelta(weeks=result_weeks - 1)
    target_friday = target_monday + timedelta(days=4)
    iso_year, iso_week, _ = target_monday.isocalendar()

    return WeekResult(
        result_weeks=result_weeks,
        iso_week=iso_week,
        iso_year=iso_year,
        week_start=target_monday,
        week_end=target_friday,
        bottleneck_key=bottleneck,
        brigade_outcomes=outcomes,
        base_outcome=base_outcome,
    )
