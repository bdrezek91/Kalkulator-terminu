"""
Modele danych Kalkulatora Terminów Pawilonów.

Logika biznesowa (normalizacja, klasyfikacja statusów, parsowanie modułów,
liczenie godzin i tygodnia) znajduje się w pawilony/services/, nie w modelach.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def import_upload_path(instance, filename):
    """Bezpieczna ścieżka uploadu — nie ufamy nazwie pliku od użytkownika."""
    import uuid

    ext = ".xlsx"
    return f"importy/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class WorkCenter(models.Model):
    """Brygada / centrum pracy: produkcja ogólna, hydraulicy, spawacze, FIBO+boazeria."""

    class Code(models.TextChoices):
        BASE = "BASE", "Produkcja ogólna"
        HYDRAULIC = "HYDRAULIC", "Hydraulicy"
        WELDING = "WELDING", "Spawacze"
        FIBO_WOOD = "FIBO_WOOD", "FIBO / boazeria"

    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Brygada / centrum pracy"
        verbose_name_plural = "Brygady / centra pracy"

    def __str__(self):
        return self.name


class OperationTime(models.Model):
    """Czas trwania (w roboczogodzinach) pojedynczej operacji, edytowalny w panelu admina."""

    work_center = models.ForeignKey(WorkCenter, on_delete=models.PROTECT, related_name="operation_times")
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    hours = models.DecimalField(max_digits=8, decimal_places=2)
    affects_term = models.BooleanField(
        default=True,
        help_text="Czy operacja ogranicza wyznaczany termin w MVP (False = tylko informacyjnie).",
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Czas operacji"
        verbose_name_plural = "Czasy operacji"
        ordering = ["work_center__code", "code"]

    def __str__(self):
        return f"{self.name} ({self.hours} h)"


class CapacityConfiguration(models.Model):
    """Konfiguracja mocy produkcyjnych i bufora bezpieczeństwa. Tylko jedna może być aktywna."""

    name = models.CharField(max_length=150, default="Domyślna konfiguracja")
    is_active = models.BooleanField(default=False)

    general_units_per_week = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("45"),
        verbose_name="Ogólna produkcja (pawilonów/tydzień)",
    )
    hydraulic_workers = models.PositiveIntegerField(default=6, verbose_name="Liczba hydraulików")
    welding_workers = models.PositiveIntegerField(default=5, verbose_name="Liczba spawaczy")
    fibo_wood_workers = models.PositiveIntegerField(default=2, verbose_name="Liczba os. FIBO/boazeria")
    hours_per_worker_week = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("40"),
        verbose_name="Godziny pracy na osobę / tydzień",
    )
    safety_buffer_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("15"),
        verbose_name="Bufor bezpieczeństwa (%)",
    )
    stale_data_warning_hours = models.PositiveIntegerField(
        default=24,
        verbose_name="Próg nieaktualności danych (godziny)",
    )
    exclude_od_reki_before_production = models.BooleanField(
        default=True,
        verbose_name="Wyklucz 'Od ręki' z kolejki przed statusem produkcji",
        help_text=(
            "Gdy włączone: pawilony o Rodzaju 'Od ręki' nie liczą się do kolejki, "
            "dopóki nie mają statusu Produkcja Zabrze albo Produkcja Czekanów "
            "(samo Logistyka ich jeszcze nie liczy). Wyłącz, żeby wrócić do liczenia "
            "'Od ręki' na każdym aktywnym statusie, tak jak 'Zamówiony'."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Konfiguracja mocy produkcyjnych"
        verbose_name_plural = "Konfiguracje mocy produkcyjnych"
        ordering = ["-is_active", "-updated_at"]

    def __str__(self):
        return f"{self.name} ({'aktywna' if self.is_active else 'nieaktywna'})"

    @property
    def buffer_factor(self) -> Decimal:
        return Decimal("1") - (self.safety_buffer_percent / Decimal("100"))

    @property
    def effective_general_capacity(self) -> Decimal:
        return self.general_units_per_week * self.buffer_factor

    @property
    def effective_hydraulic_capacity_hours(self) -> Decimal:
        return Decimal(self.hydraulic_workers) * self.hours_per_worker_week * self.buffer_factor

    @property
    def effective_welding_capacity_hours(self) -> Decimal:
        return Decimal(self.welding_workers) * self.hours_per_worker_week * self.buffer_factor

    @property
    def effective_fibo_wood_capacity_hours(self) -> Decimal:
        return Decimal(self.fibo_wood_workers) * self.hours_per_worker_week * self.buffer_factor

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            CapacityConfiguration.objects.exclude(pk=self.pk).update(is_active=False)


class ManualBacklogAdjustment(models.Model):
    """
    Ręczna korekta backlogu godzin dla danej brygady (np. gdy eksport nie zawiera
    jeszcze kolumn FIBO/boazeria). Dodawana do obciążenia wyliczonego z importu.
    """

    class Brygada(models.TextChoices):
        HYDRAULIC = "HYDRAULIC", "Hydraulicy"
        WELDING = "WELDING", "Spawacze"
        FIBO_WOOD = "FIBO_WOOD", "FIBO / boazeria"

    work_center_code = models.CharField(max_length=20, choices=Brygada.choices)
    hours = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(verbose_name="Uzasadnienie")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ręczna korekta backlogu"
        verbose_name_plural = "Ręczne korekty backlogu"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_work_center_code_display()}: {self.hours} h ({'aktywna' if self.is_active else 'nieaktywna'})"


class ImportBatch(models.Model):
    """Pojedynczy import pliku XLSX z Optimy — pełna migawka kolejki produkcyjnej."""

    class Status(models.TextChoices):
        PENDING_VALIDATION = "PENDING_VALIDATION", "Oczekuje na zatwierdzenie"
        VALIDATED = "VALIDATED", "Zwalidowany"
        COMMITTED = "COMMITTED", "Zatwierdzony"
        FAILED = "FAILED", "Błąd"
        REJECTED = "REJECTED", "Odrzucony"

    file = models.FileField(upload_to=import_upload_path)
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_VALIDATION)
    report = models.JSONField(default=dict, blank=True)
    is_active_snapshot = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Import"
        verbose_name_plural = "Importy"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Import {self.original_filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"


class PavilionSnapshot(models.Model):
    """Pojedynczy wiersz migawki kolejki produkcyjnej pochodzący z importu."""

    class StatusClass(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktywny"
        ENDED = "ENDED", "Zakończony"
        UNRECOGNIZED = "UNRECOGNIZED", "Nierozpoznany"
        EMPTY = "EMPTY", "Pusty"
        CONFLICT = "CONFLICT", "Konflikt"

    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="pavilions")

    kod = models.CharField(max_length=100, blank=True)
    nazwa = models.CharField(max_length=500, blank=True)
    typ = models.CharField(max_length=50, blank=True)
    stan_zasobow = models.CharField(max_length=200, blank=True)
    ilosc_dostepna = models.CharField(max_length=50, blank=True)
    jm = models.CharField(max_length=20, blank=True)
    oddzial = models.CharField(max_length=200, blank=True)

    rodzaj_raw = models.CharField(max_length=200, blank=True)
    rodzaj_normalized = models.CharField(max_length=200, blank=True)

    status_raw = models.CharField(max_length=300, blank=True)
    status_normalized = models.CharField(max_length=200, blank=True)
    status_classification = models.CharField(max_length=20, choices=StatusClass.choices)

    termin_realiz_raw = models.CharField(max_length=200, blank=True)

    module_raw_text = models.CharField(max_length=500, blank=True)
    module_number = models.PositiveIntegerField(null=True, blank=True)
    module_present = models.BooleanField(default=False)
    module_conflict = models.BooleanField(default=False)

    kuchnia = models.CharField(max_length=20, blank=True)
    toaleta = models.CharField(max_length=20, blank=True)
    lazienka = models.CharField(max_length=20, blank=True)
    prysznic = models.BooleanField(default=False)
    pelna_statyka = models.BooleanField(default=False)
    kratownica = models.BooleanField(default=False)

    stolarka_nst_raw = models.CharField(max_length=50, blank=True)
    zaluzje_fasadowe_raw = models.CharField(max_length=50, blank=True)
    rolety_raw = models.CharField(max_length=50, blank=True)
    plyty_niestandard_raw = models.CharField(max_length=200, blank=True)
    inne_niestandard_raw = models.CharField(max_length=200, blank=True)

    attributes_raw = models.JSONField(default=dict, blank=True)

    is_counted = models.BooleanField(default=False, help_text="Czy liczony do aktualnego backlogu")
    is_custom = models.BooleanField(default=False, help_text="Niestandardowy — obciąża co najmniej jedną brygadę")

    hydraulic_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    welding_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    fibo_wood_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))

    conflict_reasons = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)

    source_row_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Pawilon (migawka)"
        verbose_name_plural = "Pawilony (migawka)"
        indexes = [
            models.Index(fields=["import_batch", "is_counted"]),
            models.Index(fields=["import_batch", "kod"]),
        ]

    def __str__(self):
        return f"{self.kod} — {self.nazwa}"[:80]


class Reservation(models.Model):
    """
    Miejsce na przyszłą funkcję rezerwacji terminu (nieaktywna w MVP).
    Model nie jest podłączony do żadnej logiki widoków w bieżącym zakresie.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Robocza"
        CONFIRMED = "CONFIRMED", "Potwierdzona"
        EXPIRED = "EXPIRED", "Wygasła"
        CANCELLED = "CANCELLED", "Anulowana"

    calculated_week_number = models.PositiveSmallIntegerField(null=True, blank=True)
    calculated_week_year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    requested_configuration = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Rezerwacja (przyszła funkcja)"
        verbose_name_plural = "Rezerwacje (przyszła funkcja)"


class Proforma(models.Model):
    """Miejsce na przyszłą integrację z kontrolą zapłaty proformy (nieaktywna w MVP)."""

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="proformas", null=True, blank=True
    )
    is_paid = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proforma (przyszła funkcja)"
        verbose_name_plural = "Proformy (przyszła funkcja)"
