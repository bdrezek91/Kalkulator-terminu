"""
Jednorazowa korekta liczby hydraulików i spawaczy na podstawie wewnętrznego
raportu produkcyjnego (Dampol, sierpień 2026): hydraulika 8 -> 6, spawalnia
7 -> 5. To świadoma, jednorazowa korekta danych — nadpisuje wartość nawet
jeśli administrator ustawił ją ręcznie na poprzednią liczbę (wzorem migracji
0002/0006), a nie stały mechanizm synchronizacji.
"""

from django.db import migrations, models


def apply_worker_counts(apps, schema_editor):
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")
    CapacityConfiguration.objects.filter(hydraulic_workers=8).update(hydraulic_workers=6)
    CapacityConfiguration.objects.filter(welding_workers=7).update(welding_workers=5)


def reverse_worker_counts(apps, schema_editor):
    CapacityConfiguration = apps.get_model("pawilony", "CapacityConfiguration")
    CapacityConfiguration.objects.filter(hydraulic_workers=6).update(hydraulic_workers=8)
    CapacityConfiguration.objects.filter(welding_workers=5).update(welding_workers=7)


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0008_split_fibo_plytki_hydraulika_fibo_wood"),
    ]

    operations = [
        migrations.AlterField(
            model_name="capacityconfiguration",
            name="hydraulic_workers",
            field=models.PositiveIntegerField(default=6, verbose_name="Liczba hydraulików"),
        ),
        migrations.AlterField(
            model_name="capacityconfiguration",
            name="welding_workers",
            field=models.PositiveIntegerField(default=5, verbose_name="Liczba spawaczy"),
        ),
        migrations.RunPython(apply_worker_counts, reverse_worker_counts),
    ]
