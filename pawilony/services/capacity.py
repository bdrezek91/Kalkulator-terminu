"""Dostęp do aktywnej konfiguracji mocy produkcyjnych i backlogu."""

from decimal import Decimal

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
    totals = {"HYDRAULIC": Decimal("0"), "WELDING": Decimal("0"), "FIBO_WOOD": Decimal("0")}
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


def fibo_wood_columns_present(batch: ImportBatch | None) -> tuple[bool, bool]:
    """Zwraca (czy_kolumna_FIBO_była_w_pliku, czy_kolumna_BOAZERIA_była_w_pliku)."""
    if batch is None:
        return False, False
    report = batch.report or {}
    return bool(report.get("fibo_column_present")), bool(report.get("boazeria_column_present"))
