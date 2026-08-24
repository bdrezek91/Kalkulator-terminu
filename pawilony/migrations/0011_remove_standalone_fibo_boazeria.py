"""
Usuwa samodzielne pozycje "FIBO" i "Boazeria" z sekcji Wykończenie (checkboxy
w kalkulatorze, kolumny FIBO/BOAZERIA w imporcie Optimy) — decyzja biznesowa
(sierpień 2026). NIE dotyczy brygady FIBO/boazeria jako takiej ani podziału
40%/60% godzin Fibo/Płytki wliczonych w warianty Komfort/Premium Toalety/
Łazienki — to zostaje bez zmian, brygada FIBO/boazeria nadal istnieje i wciąż
liczy godziny z tego podziału.

Usuwa OperationTime "fibo"/"boazeria" (50h/70h, work_center=FIBO_WOOD) —
work_center sam zostaje, bo wciąż mają na nim swoje kody podziału Fibo/Płytki.
"""

from django.db import migrations


def remove_fibo_boazeria_operations(apps, schema_editor):
    OperationTime = apps.get_model("pawilony", "OperationTime")
    OperationTime.objects.filter(code__in=["fibo", "boazeria"]).delete()


def restore_fibo_boazeria_operations(apps, schema_editor):
    from decimal import Decimal

    WorkCenter = apps.get_model("pawilony", "WorkCenter")
    OperationTime = apps.get_model("pawilony", "OperationTime")

    fibo_wood_wc = WorkCenter.objects.filter(code="FIBO_WOOD").first()
    if fibo_wood_wc is None:
        return
    OperationTime.objects.get_or_create(
        code="fibo",
        defaults={
            "name": "FIBO",
            "work_center": fibo_wood_wc,
            "hours": Decimal("50"),
            "affects_term": True,
            "is_active": True,
        },
    )
    OperationTime.objects.get_or_create(
        code="boazeria",
        defaults={
            "name": "Boazeria",
            "work_center": fibo_wood_wc,
            "hours": Decimal("70"),
            "affects_term": True,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0010_remove_custom_bathroom_brigade"),
    ]

    operations = [
        migrations.RunPython(remove_fibo_boazeria_operations, restore_fibo_boazeria_operations),
        migrations.RemoveField(
            model_name="pavilionsnapshot",
            name="boazeria",
        ),
        migrations.RemoveField(
            model_name="pavilionsnapshot",
            name="fibo",
        ),
    ]
