"""
Wyliczanie roboczogodzin brygad na podstawie wyposażenia pawilonu.

Jedno źródło prawdy używane zarówno przez import (na podstawie atrybutów
z Excela), jak i przez publiczny kalkulator (na podstawie formularza).
"""

from dataclasses import dataclass, field
from decimal import Decimal

from pawilony.models import OperationTime

HYDRAULIC_CODES = {
    ("kuchnia", "standard"): "kuchnia_standard",
    ("kuchnia", "lux"): "kuchnia_lux",
    ("toaleta", "standard"): "toaleta_standard",
    ("toaleta", "komfort"): "toaleta_komfort",
    ("toaleta", "premium"): "toaleta_premium",
    ("lazienka", "standard"): "lazienka_standard",
    ("lazienka", "komfort"): "lazienka_komfort",
    ("lazienka", "premium"): "lazienka_premium",
}
# Godziny Fibo/Płytki wliczone na stałe w warianty Komfort/Premium Toalety
# i Łazienki (nie są osobnymi dodatkami) są DZIELONE 40%/60% między hydraulikę
# a brygadę FIBO/boazeria — HYDRAULIC_CODES powyżej wskazuje na kod z już
# zmniejszoną wartością (40%), a FIBO_SPLIT_CODES wskazuje pozostałe 60%,
# liczone do brygady FIBO/boazeria. Tylko Toaleta/Łazienka Komfort/Premium
# mają taki podział — Standard i Kuchnia nie mają w ogóle Fibo/Płytki
# wliczonych, więc nie występują w tej mapie.
FIBO_SPLIT_CODES = {
    ("toaleta", "komfort"): "toaleta_komfort_fibo_split",
    ("toaleta", "premium"): "toaleta_premium_fibo_split",
    ("lazienka", "komfort"): "lazienka_komfort_fibo_split",
    ("lazienka", "premium"): "lazienka_premium_fibo_split",
}
PRYSZNIC_CODE = "prysznic_samodzielny"
STATYKA_CODE = "statyka_pelna"
KRATOWNICA_CODE = "kratownica"
INFO_CODES = {
    "stolarka_nst": "stolarka_nst",
    "zaluzje_fasadowe": "zaluzje_fasadowe",
    "rolety": "rolety",
}

KUCHNIA_CHOICES = {"standard": "Standard", "lux": "Lux"}
WARIANT_CHOICES = {"standard": "Standard", "komfort": "Komfort", "premium": "Premium"}


def get_operation_hours_map() -> dict[str, Decimal]:
    """Aktualne, aktywne czasy operacji z bazy, code -> godziny (Decimal)."""
    return {op.code: op.hours for op in OperationTime.objects.filter(is_active=True)}


@dataclass
class PavilionEquipment:
    """Znormalizowane wyposażenie pawilonu wykorzystywane do liczenia godzin."""

    kuchnia: str | None = None  # 'Standard' | 'Lux' | None
    # Liczba aneksów kuchennych — mnoży godziny wybranego wariantu Kuchni.
    kuchnia_count: int = 1
    toaleta: str | None = None  # 'Standard' | 'Komfort' | 'Premium' | None
    lazienka: str | None = None  # 'Standard' | 'Komfort' | 'Premium' | None
    prysznic: bool = False
    # Liczba łazienek/toalet — mnoży godziny wybranego wariantu Toalety/Łazienki
    # (w tym wliczoną część Fibo/Płytki) oraz samodzielnego prysznica.
    bathroom_count: int = 1
    pelna_statyka: bool = False
    kratownica: bool = False
    # Liczba modułów pawilonu (projekty wielomodułowe, np. "MODUŁ 1/2/3" w nazwie) —
    # statyka/kratownica są liczone RAZY liczba modułów, bo każdy moduł wymaga
    # własnej konstrukcji spawanej. Pozostałe brygady (hydraulika, FIBO/boazeria)
    # są liczone per pawilon/wariant, niezależnie od liczby modułów.
    module_count: int = 1
    stolarka_nst: bool = False
    zaluzje_fasadowe: bool = False
    rolety: bool = False


@dataclass
class HoursResult:
    hydraulic_hours: Decimal = Decimal("0")
    welding_hours: Decimal = Decimal("0")
    fibo_wood_hours: Decimal = Decimal("0")
    informational_hours: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)

    @property
    def is_custom(self) -> bool:
        return (
            self.hydraulic_hours > 0
            or self.welding_hours > 0
            or self.fibo_wood_hours > 0
        )


def _op_hours(op_hours: dict[str, Decimal], code: str, warnings: list[str]) -> Decimal:
    val = op_hours.get(code)
    if val is None:
        warnings.append(f"Brak zdefiniowanego czasu operacji '{code}' w konfiguracji — pominięto.")
        return Decimal("0")
    return val


def calculate_hours(equipment: PavilionEquipment, op_hours: dict[str, Decimal] | None = None) -> HoursResult:
    if op_hours is None:
        op_hours = get_operation_hours_map()

    warnings: list[str] = []
    hydraulic = Decimal("0")
    welding = Decimal("0")
    fibo_wood = Decimal("0")
    informational = Decimal("0")

    kuchnia_count = max(equipment.kuchnia_count, 1)
    if equipment.kuchnia:
        key = equipment.kuchnia.strip().lower()
        code = HYDRAULIC_CODES.get(("kuchnia", key))
        if code:
            hydraulic += _op_hours(op_hours, code, warnings) * kuchnia_count
        else:
            warnings.append(f"Nierozpoznany wariant kuchni: '{equipment.kuchnia}'")

    bathroom_count = max(equipment.bathroom_count, 1)
    if equipment.lazienka:
        key = equipment.lazienka.strip().lower()
        code = HYDRAULIC_CODES.get(("lazienka", key))
        if code:
            hydraulic += _op_hours(op_hours, code, warnings) * bathroom_count
            split_code = FIBO_SPLIT_CODES.get(("lazienka", key))
            if split_code:
                fibo_wood += _op_hours(op_hours, split_code, warnings) * bathroom_count
        else:
            warnings.append(f"Nierozpoznany wariant łazienki: '{equipment.lazienka}'")
    else:
        if equipment.toaleta:
            key = equipment.toaleta.strip().lower()
            code = HYDRAULIC_CODES.get(("toaleta", key))
            if code:
                hydraulic += _op_hours(op_hours, code, warnings) * bathroom_count
                split_code = FIBO_SPLIT_CODES.get(("toaleta", key))
                if split_code:
                    fibo_wood += _op_hours(op_hours, split_code, warnings) * bathroom_count
            else:
                warnings.append(f"Nierozpoznany wariant toalety: '{equipment.toaleta}'")
        if equipment.prysznic:
            hydraulic += _op_hours(op_hours, PRYSZNIC_CODE, warnings) * bathroom_count

    module_count = max(equipment.module_count, 1)
    if equipment.pelna_statyka:
        welding += _op_hours(op_hours, STATYKA_CODE, warnings) * module_count
    if equipment.kratownica:
        welding += _op_hours(op_hours, KRATOWNICA_CODE, warnings) * module_count

    if equipment.stolarka_nst:
        informational += _op_hours(op_hours, INFO_CODES["stolarka_nst"], warnings)
    if equipment.zaluzje_fasadowe:
        informational += _op_hours(op_hours, INFO_CODES["zaluzje_fasadowe"], warnings)
    if equipment.rolety:
        informational += _op_hours(op_hours, INFO_CODES["rolety"], warnings)

    return HoursResult(
        hydraulic_hours=hydraulic,
        welding_hours=welding,
        fibo_wood_hours=fibo_wood,
        informational_hours=informational,
        warnings=warnings,
    )
