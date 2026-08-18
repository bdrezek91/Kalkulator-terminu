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
        "CUSTOM_BATHROOM": Decimal("0"),
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
            custom_bathroom_hours=manual["CUSTOM_BATHROOM"],
        )

    counted = batch.pavilions.filter(is_counted=True)
    base_units = counted.count()

    from django.db.models import Sum

    sums = counted.aggregate(
        hydraulic=Sum("hydraulic_hours"),
        welding=Sum("welding_hours"),
        fibo_wood=Sum("fibo_wood_hours"),
        custom_bathroom=Sum("custom_bathroom_hours"),
    )

    return BacklogTotals(
        base_units=base_units,
        hydraulic_hours=(sums["hydraulic"] or Decimal("0")) + manual["HYDRAULIC"],
        welding_hours=(sums["welding"] or Decimal("0")) + manual["WELDING"],
        fibo_wood_hours=(sums["fibo_wood"] or Decimal("0")) + manual["FIBO_WOOD"],
        custom_bathroom_hours=(sums["custom_bathroom"] or Decimal("0")) + manual["CUSTOM_BATHROOM"],
    )


def fibo_wood_columns_present(batch: ImportBatch | None) -> tuple[bool, bool]:
    """Zwraca (czy_kolumna_FIBO_była_w_pliku, czy_kolumna_BOAZERIA_była_w_pliku)."""
    if batch is None:
        return False, False
    report = batch.report or {}
    return bool(report.get("fibo_column_present")), bool(report.get("boazeria_column_present"))


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
    fibo_count: int = 0
    boazeria_count: int = 0
    # Niezależne dodatki WC/łazienki (własna pula mocy) — patrz uwaga w
    # compute_equipment_breakdown o braku kolumn źródłowych w Optimie.
    wc_addon_fibo_count: int = 0
    wc_addon_plytki_count: int = 0
    wc_addon_boazeria_count: int = 0


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
        fibo_count=counted.filter(fibo=True).count(),
        boazeria_count=counted.filter(boazeria=True).count(),
        # Eksport Optima nie ma jeszcze osobnych kolumn dla tych dodatków —
        # zawsze 0, dopóki firma nie doda odpowiednich atrybutów do eksportu.
        wc_addon_fibo_count=counted.filter(wc_fibo=True).count(),
        wc_addon_plytki_count=counted.filter(wc_plytki=True).count(),
        wc_addon_boazeria_count=counted.filter(wc_boazeria=True).count(),
    )
