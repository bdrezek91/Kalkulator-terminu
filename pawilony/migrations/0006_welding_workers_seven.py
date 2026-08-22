"""
Jednorazowa korekta liczby spawaczy: 8 -> 7 (rzeczywisty stan zespołu,
sierpień 2026). Aktualizuje pole modelu (nowy default dla przyszłych
konfiguracji) oraz istniejącą aktywną konfigurację mocy produkcyjnych —
to świadoma, jednorazowa korekta danych, nie stały mechanizm synchronizacji,
więc nadpisuje wartość nawet jeśli administrator ustawił ją ręcznie na 8.
"""

from django.db import migrations, models


def set_welding_workers_seven(apps, schema_editor):
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")
    CapacityConfiguration.objects.filter(welding_workers=8).update(welding_workers=7)


def reverse_set_welding_workers_seven(apps, schema_editor):
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")
    CapacityConfiguration.objects.filter(welding_workers=7).update(welding_workers=8)


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0005_fold_fibo_plytki_into_tiers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="capacityconfiguration",
            name="welding_workers",
            field=models.PositiveIntegerField(default=7, verbose_name="Liczba spawaczy"),
        ),
        migrations.RunPython(set_welding_workers_seven, reverse_set_welding_workers_seven),
    ]
