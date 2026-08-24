"""
Usuwa całkowicie grupę "Niestandardowe łazienki" (dodatek Boazeria WC/łazienka,
150h, własna pula mocy CUSTOM_BATHROOM) — decyzja biznesowa (sierpień 2026).

Ta funkcja nigdy nie była zasilana z importu XLSX (brak mapowania kolumny w
header_mapping.py) — istniała wyłącznie jako pole w publicznym kalkulatorze
(bez zapisu do bazy) oraz jako możliwy cel ręcznej korekty backlogu w panelu
admina. Usunięcie nie dotyka więc żadnych rzeczywistych danych z importów;
jedyne realne dane, które znikają, to ewentualne ręczne korekty backlogu na
tę brygadę (CUSTOM_BATHROOM) — jeśli administrator jakieś utworzył.

Kolejność w RunPython jest wymuszona przez ograniczenie klucza obcego
OperationTime.work_center (on_delete=PROTECT): najpierw usuwamy operację
"wc_addon_boazeria", dopiero potem sam WorkCenter "CUSTOM_BATHROOM".
"""

from django.db import migrations, models


def remove_custom_bathroom(apps, schema_editor):
    WorkCenter = apps.get_model("pawilony", "WorkCenter")
    OperationTime = apps.get_model("pawilony", "OperationTime")
    ManualBacklogAdjustment = apps.get_model("pawilony", "ManualBacklogAdjustment")

    OperationTime.objects.filter(code="wc_addon_boazeria").delete()
    ManualBacklogAdjustment.objects.filter(work_center_code="CUSTOM_BATHROOM").delete()
    WorkCenter.objects.filter(code="CUSTOM_BATHROOM").delete()


def restore_custom_bathroom(apps, schema_editor):
    from decimal import Decimal

    WorkCenter = apps.get_model("pawilony", "WorkCenter")
    OperationTime = apps.get_model("pawilony", "OperationTime")

    wc, _ = WorkCenter.objects.get_or_create(
        code="CUSTOM_BATHROOM", defaults={"name": "Niestandardowe łazienki"}
    )
    OperationTime.objects.get_or_create(
        code="wc_addon_boazeria",
        defaults={
            "name": "WC/łazienka: Boazeria (dodatkowo)",
            "work_center": wc,
            "hours": Decimal("150"),
            "affects_term": True,
            "is_active": True,
        },
    )
    # Ręczne korekty backlogu na tę brygadę oraz pole wc_boazeria na
    # PavilionSnapshot NIE są odtwarzane — to nieodwracalna część tej migracji.


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0009_hydraulic_welding_workers_from_reference_report"),
    ]

    operations = [
        migrations.RunPython(remove_custom_bathroom, restore_custom_bathroom),
        migrations.RemoveField(
            model_name="capacityconfiguration",
            name="custom_bathroom_workers",
        ),
        migrations.RemoveField(
            model_name="pavilionsnapshot",
            name="wc_boazeria",
        ),
        migrations.RemoveField(
            model_name="pavilionsnapshot",
            name="custom_bathroom_hours",
        ),
        migrations.AlterField(
            model_name="workcenter",
            name="code",
            field=models.CharField(
                choices=[
                    ("BASE", "Produkcja ogólna"),
                    ("HYDRAULIC", "Hydraulicy"),
                    ("WELDING", "Spawacze"),
                    ("FIBO_WOOD", "FIBO / boazeria"),
                ],
                max_length=20,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="manualbacklogadjustment",
            name="work_center_code",
            field=models.CharField(
                choices=[
                    ("HYDRAULIC", "Hydraulicy"),
                    ("WELDING", "Spawacze"),
                    ("FIBO_WOOD", "FIBO / boazeria"),
                ],
                max_length=20,
            ),
        ),
    ]
