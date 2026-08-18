from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from pawilony.models import CapacityConfiguration, OperationTime, WorkCenter

WORK_CENTERS = [
    (WorkCenter.Code.BASE, "Produkcja ogólna"),
    (WorkCenter.Code.HYDRAULIC, "Hydraulicy"),
    (WorkCenter.Code.WELDING, "Spawacze"),
    (WorkCenter.Code.FIBO_WOOD, "FIBO / boazeria"),
    (WorkCenter.Code.CUSTOM_BATHROOM, "Niestandardowe łazienki"),
]

# code, name, work_center, hours, affects_term
OPERATION_TIMES = [
    # Wartości hydrauliki potwierdzone z produkcją (korespondencja Dampol/DIT, sierpień 2026,
    # druga tura): Kuchnia — jedna stawka niezależnie od wariantu. Toaleta/Łazienka Komfort
    # i Premium mają na stałe wliczone godziny Fibo/Płytki (nie są to osobne dodatki) —
    # Łazienka: Standard 7h, Komfort 10+80=90h, Premium 10+90=100h;
    # Toaleta:  Standard 7h, Komfort 12+40=52h, Premium 10+45=55h.
    ("kuchnia_standard", "Kuchnia Standard", WorkCenter.Code.HYDRAULIC, "10", True),
    ("kuchnia_lux", "Kuchnia Lux", WorkCenter.Code.HYDRAULIC, "10", True),
    ("toaleta_standard", "Toaleta Standard", WorkCenter.Code.HYDRAULIC, "7", True),
    ("toaleta_komfort", "Toaleta Komfort", WorkCenter.Code.HYDRAULIC, "52", True),
    ("toaleta_premium", "Toaleta Premium", WorkCenter.Code.HYDRAULIC, "55", True),
    # Boazeria WC/łazienki jest jedynym pozostałym niezależnym, łączalnym dodatkiem
    # (dowolny wariant Toalety/Łazienki) — ma WŁASNĄ pulę mocy (CUSTOM_BATHROOM).
    ("wc_addon_boazeria", "WC/łazienka: Boazeria (dodatkowo)", WorkCenter.Code.CUSTOM_BATHROOM, "150", True),
    ("lazienka_standard", "Łazienka Standard", WorkCenter.Code.HYDRAULIC, "7", True),
    ("lazienka_komfort", "Łazienka Komfort", WorkCenter.Code.HYDRAULIC, "90", True),
    ("lazienka_premium", "Łazienka Premium", WorkCenter.Code.HYDRAULIC, "100", True),
    ("prysznic_samodzielny", "Samodzielny prysznic", WorkCenter.Code.HYDRAULIC, "8", True),
    ("statyka_pelna", "Pełna konstrukcja / statyka", WorkCenter.Code.WELDING, "12", True),
    ("kratownica", "Kratownica", WorkCenter.Code.WELDING, "4", True),
    ("fibo", "FIBO", WorkCenter.Code.FIBO_WOOD, "50", True),
    ("boazeria", "Boazeria", WorkCenter.Code.FIBO_WOOD, "70", True),
    ("stolarka_nst", "Stolarka niestandardowa", WorkCenter.Code.HYDRAULIC, "5", False),
    ("zaluzje_fasadowe", "Żaluzje fasadowe", WorkCenter.Code.HYDRAULIC, "5", False),
    ("rolety", "Rolety", WorkCenter.Code.HYDRAULIC, "5", False),
]


class Command(BaseCommand):
    help = "Wgrywa domyślną konfigurację: brygady, czasy operacji i aktywną konfigurację mocy produkcyjnych."

    @transaction.atomic
    def handle(self, *args, **options):
        centers = {}
        for code, name in WORK_CENTERS:
            wc, _ = WorkCenter.objects.get_or_create(code=code, defaults={"name": name})
            centers[code] = wc

        for code, name, wc_code, hours, affects_term in OPERATION_TIMES:
            OperationTime.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "work_center": centers[wc_code],
                    "hours": Decimal(hours),
                    "affects_term": affects_term,
                    "is_active": True,
                },
            )

        if not CapacityConfiguration.objects.filter(is_active=True).exists():
            CapacityConfiguration.objects.create(
                name="Domyślna konfiguracja",
                is_active=True,
                general_units_per_week=Decimal("45"),
                hydraulic_workers=8,
                welding_workers=7,
                fibo_wood_workers=3,
                custom_bathroom_workers=3,
                hours_per_worker_week=Decimal("40"),
                safety_buffer_percent=Decimal("15"),
                stale_data_warning_hours=24,
            )

        self.stdout.write(self.style.SUCCESS("Domyślna konfiguracja została wgrana."))
