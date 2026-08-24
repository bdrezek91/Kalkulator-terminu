"""
Godziny Fibo/Płytki wliczone na stałe w warianty Komfort/Premium Toalety
i Łazienki są dzielone w proporcji 40% hydraulika / 60% brygada FIBO/boazeria
— "monterzy fibo/płytek/boazerii" mają obecnie 2 osoby (korespondencja
Dampol/DIT, sierpień 2026, trzecia-piąta tura).

Toaleta Komfort/Premium ustawiona jest jako dokładnie połowa odpowiadającego
wariantu Łazienki (w obu składowych — hydraulika i FIBO/boazeria):
- Łazienka Komfort: 90h razem -> 36h hydraulika (40%) + 54h FIBO/boazeria (60%)
- Łazienka Premium: 100h razem -> 40h hydraulika + 60h FIBO/boazeria
- Toaleta Komfort: 45h razem (połowa Łazienki) -> 18h hydraulika + 27h FIBO/boazeria
- Toaleta Premium: 50h razem (połowa Łazienki) -> 20h hydraulika + 30h FIBO/boazeria

Dodatkowo koryguje liczbę osób w brygadzie FIBO/boazeria: 3 -> 2.
"""

from decimal import Decimal

from django.db import migrations, models

HYDRAULIC_HOURS_NEW = {
    "lazienka_komfort": "36",
    "lazienka_premium": "40",
    "toaleta_komfort": "18",
    "toaleta_premium": "20",
}
HYDRAULIC_HOURS_OLD = {
    "lazienka_komfort": "90",
    "lazienka_premium": "100",
    "toaleta_komfort": "52",
    "toaleta_premium": "55",
}

FIBO_SPLIT_CODES = {
    "lazienka_komfort_fibo_split": ("Łazienka Komfort: Fibo/Płytki (60%)", "54"),
    "lazienka_premium_fibo_split": ("Łazienka Premium: Fibo/Płytki (60%)", "60"),
    "toaleta_komfort_fibo_split": ("Toaleta Komfort: Fibo/Płytki (60%)", "27"),
    "toaleta_premium_fibo_split": ("Toaleta Premium: Fibo/Płytki (60%)", "30"),
}


def apply_split(apps, schema_editor):
    WorkCenter = apps.get_model("pawilony", "WorkCenter")
    OperationTime = apps.get_model("pawilony", "OperationTime")
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")

    for code, hours in HYDRAULIC_HOURS_NEW.items():
        OperationTime.objects.filter(code=code).update(hours=Decimal(hours))

    fibo_wood_wc, _ = WorkCenter.objects.get_or_create(
        code="FIBO_WOOD", defaults={"name": "FIBO / boazeria"}
    )
    for code, (name, hours) in FIBO_SPLIT_CODES.items():
        OperationTime.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "work_center": fibo_wood_wc,
                "hours": Decimal(hours),
                "affects_term": True,
                "is_active": True,
            },
        )

    CapacityConfiguration.objects.filter(fibo_wood_workers=3).update(fibo_wood_workers=2)


def reverse_split(apps, schema_editor):
    OperationTime = apps.get_model("pawilony", "OperationTime")
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")

    for code, hours in HYDRAULIC_HOURS_OLD.items():
        OperationTime.objects.filter(code=code).update(hours=Decimal(hours))

    OperationTime.objects.filter(code__in=FIBO_SPLIT_CODES.keys()).delete()

    CapacityConfiguration.objects.filter(fibo_wood_workers=2).update(fibo_wood_workers=3)


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0007_od_reki_toggle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="capacityconfiguration",
            name="fibo_wood_workers",
            field=models.PositiveIntegerField(default=2, verbose_name="Liczba os. FIBO/boazeria"),
        ),
        migrations.RunPython(apply_split, reverse_split),
    ]
