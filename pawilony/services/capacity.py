"""Dostęp do aktywnej konfiguracji mocy produkcyjnych i backlogu."""

from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Count

from pawilony.models import CapacityConfiguration, ImportBatch, ManualBacklogAdjustment
from pawilony.services.week_calculation import BacklogTotals


class NoActiveConfigurationError(Exception):
    pass


def get_active_configuration() -> CapacityConfiguration:
    config = CapacityConfiguration.objects.filter(is_active=True).first()
    if config is None:
        raise NoActiveConfigurationError(
            "Brak aktywnej konfiguracji mocy produkcyjnych. Skontaktuj się z administratorem."
        )
    return config


def get_active_import_batch() -> ImportBatch | None:
    return ImportBatch.objects.filter(is_active_snapshot=True, status=ImportBatch.Status.COMMITTED).first()


def manual_adjustment_totals() -> dict[str, Decimal]:
    totals = {
        "HYDRAULIC": Decimal("0"),
        "WELDING": Decimal("0"),
        "FIBO_WOOD": Decimal("0"),
    }
    qs = ManualBacklogAdjustment.objects.filter(is_active=True)
    for adj in qs:
        totals[adj.work_center_code] = totals.get(adj.work_center_code, Decimal("0")) + adj.hours
    return totals


def compute_backlog_totals(batch: ImportBatch | None) -> BacklogTotals:
    manual = manual_adjustment_totals()
    if batch is None:
        return BacklogTotals(
            base_units=0,
            hydraulic_hours=manual["HYDRAULIC"],
            welding_hours=manual["WELDING"],
            fibo_wood_hours=manual["FIBO_WOOD"],
        )

    counted = batch.pavilions.filter(is_counted=True)
    base_units = counted.count()

    from django.db.models import Sum

    sums = counted.aggregate(
        hydraulic=Sum("hydraulic_hours"),
        welding=Sum("welding_hours"),
        fibo_wood=Sum("fibo_wood_hours"),
    )

    return BacklogTotals(
        base_units=base_units,
        hydraulic_hours=(sums["hydraulic"] or Decimal("0")) + manual["HYDRAULIC"],
        welding_hours=(sums["welding"] or Decimal("0")) + manual["WELDING"],
        fibo_wood_hours=(sums["fibo_wood"] or Decimal("0")) + manual["FIBO_WOOD"],
    )


@dataclass
class EquipmentBreakdown:
    """
    Zagregowane, publiczne podsumowanie tego, z czego wynika obecne obciążenie
    brygad — wyłącznie liczby wg typu wyposażenia, bez kodów/nazw/numerów
    projektów pojedynczych pawilonów.
    """

    total_counted: int = 0
    standard_count: int = 0
    custom_count: int = 0
    kuchnia: dict[str, int] = field(default_factory=dict)
    toaleta: dict[str, int] = field(default_factory=dict)
    lazienka: dict[str, int] = field(default_factory=dict)
    prysznic_count: int = 0
    statyka_count: int = 0
    kratownica_count: int = 0


def _value_counts(queryset, field_name: str) -> dict[str, int]:
    rows = (
        queryset.exclude(**{field_name: ""})
        .values(field_name)
        .annotate(n=Count("id"))
        .order_by(field_name)
    )
    return {row[field_name]: row["n"] for row in rows}


def compute_equipment_breakdown(batch: ImportBatch | None) -> EquipmentBreakdown:
    if batch is None:
        return EquipmentBreakdown()

    counted = batch.pavilions.filter(is_counted=True)
    # Toaleta i samodzielny prysznic liczą się do godzin tylko wtedy, gdy nie
    # ma łazienki (łazienka jest kompletem) — podsumowanie ma odzwierciedlać
    # realne obciążenie, więc pomijamy je tam, gdzie łazienka je zastępuje.
    no_lazienka = counted.filter(lazienka="")

    return EquipmentBreakdown(
        total_counted=counted.count(),
        standard_count=counted.filter(is_custom=False).count(),
        custom_count=counted.filter(is_custom=True).count(),
        kuchnia=_value_counts(counted, "kuchnia"),
        toaleta=_value_counts(no_lazienka, "toaleta"),
        lazienka=_value_counts(counted, "lazienka"),
        prysznic_count=no_lazienka.filter(prysznic=True).count(),
        statyka_count=counted.filter(pelna_statyka=True).count(),
        kratownica_count=counted.filter(kratownica=True).count(),
    )
