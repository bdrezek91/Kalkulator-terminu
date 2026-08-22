"""
Jednorazowa korekta czasów operacji hydrauliki na wartości potwierdzone
z produkcją (korespondencja Dampol/DIT, sierpień 2026).

Aktualizuje tylko istniejące wiersze OperationTime o dopasowanym `code` —
nie tworzy nowych (to robi seed_defaults) i nie rusza żadnych innych brygad.
Jeżeli administrator w międzyczasie ręcznie ustawił inną wartość dla danego
kodu, ta migracja i tak nadpisze ją nowo potwierdzoną liczbą — to świadoma,
jednorazowa korekta danych, a nie stały mechanizm synchronizacji.
"""

from decimal import Decimal

from django.db import migrations

NEW_HOURS = {
    "kuchnia_standard": "10",
    "kuchnia_lux": "10",
    "toaleta_standard": "7",
    "toaleta_komfort": "12",
    "toaleta_premium": "10",
    "lazienka_standard": "7",
    "lazienka_komfort": "10",
    "lazienka_premium": "10",
}


def update_hours(apps, schema_editor):
    OperationTime = apps.get_model("pawilony", "OperationTime")
    for code, hours in NEW_HOURS.items():
        OperationTime.objects.filter(code=code).update(hours=Decimal(hours))


def reverse_update_hours(apps, schema_editor):
    OperationTime = apps.get_model("pawilony", "OperationTime")
    previous_hours = {
        "kuchnia_standard": "8",
        "kuchnia_lux": "10",
        "toaleta_standard": "6",
        "toaleta_komfort": "7",
        "toaleta_premium": "8",
        "lazienka_standard": "10",
        "lazienka_komfort": "11",
        "lazienka_premium": "12",
    }
    for code, hours in previous_hours.items():
        OperationTime.objects.filter(code=code).update(hours=Decimal(hours))


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(update_hours, reverse_update_hours),
    ]
