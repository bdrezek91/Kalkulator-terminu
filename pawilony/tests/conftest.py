from decimal import Decimal

import pytest

from pawilony.models import CapacityConfiguration, OperationTime, WorkCenter


@pytest.fixture
def work_centers(db):
    centers = {}
    for code, name in [
        (WorkCenter.Code.BASE, "Produkcja ogólna"),
        (WorkCenter.Code.HYDRAULIC, "Hydraulicy"),
        (WorkCenter.Code.WELDING, "Spawacze"),
        (WorkCenter.Code.FIBO_WOOD, "FIBO / boazeria"),
    ]:
        centers[code], _ = WorkCenter.objects.get_or_create(code=code, defaults={"name": name})
    return centers


@pytest.fixture
def operation_times(work_centers):
    data = [
        ("kuchnia_standard", "Kuchnia Standard", WorkCenter.Code.HYDRAULIC, "8", True),
        ("kuchnia_lux", "Kuchnia Lux", WorkCenter.Code.HYDRAULIC, "10", True),
        ("toaleta_standard", "Toaleta Standard", WorkCenter.Code.HYDRAULIC, "6", True),
        ("toaleta_komfort", "Toaleta Komfort", WorkCenter.Code.HYDRAULIC, "7", True),
        ("toaleta_premium", "Toaleta Premium", WorkCenter.Code.HYDRAULIC, "8", True),
        ("lazienka_standard", "Łazienka Standard", WorkCenter.Code.HYDRAULIC, "10", True),
        ("lazienka_komfort", "Łazienka Komfort", WorkCenter.Code.HYDRAULIC, "11", True),
        ("lazienka_premium", "Łazienka Premium", WorkCenter.Code.HYDRAULIC, "12", True),
        ("prysznic_samodzielny", "Samodzielny prysznic", WorkCenter.Code.HYDRAULIC, "8", True),
        ("statyka_pelna", "Pełna konstrukcja / statyka", WorkCenter.Code.WELDING, "12", True),
        ("kratownica", "Kratownica", WorkCenter.Code.WELDING, "4", True),
        ("fibo", "FIBO", WorkCenter.Code.FIBO_WOOD, "50", True),
        ("boazeria", "Boazeria", WorkCenter.Code.FIBO_WOOD, "70", True),
        ("stolarka_nst", "Stolarka niestandardowa", WorkCenter.Code.HYDRAULIC, "5", False),
        ("zaluzje_fasadowe", "Żaluzje fasadowe", WorkCenter.Code.HYDRAULIC, "5", False),
        ("rolety", "Rolety", WorkCenter.Code.HYDRAULIC, "5", False),
    ]
    result = {}
    for code, name, wc_code, hours, affects_term in data:
        op, _ = OperationTime.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "work_center": work_centers[wc_code],
                "hours": Decimal(hours),
                "affects_term": affects_term,
                "is_active": True,
            },
        )
        result[code] = op
    return result


@pytest.fixture
def active_config(db):
    return CapacityConfiguration.objects.create(
        name="Test",
        is_active=True,
        general_units_per_week=Decimal("45"),
        hydraulic_workers=8,
        welding_workers=8,
        fibo_wood_workers=3,
        hours_per_worker_week=Decimal("40"),
        safety_buffer_percent=Decimal("15"),
        stale_data_warning_hours=24,
    )
