"""
Przełącznik w Konfiguracji mocy produkcyjnych pozwalający włączyć/wyłączyć
regułę "Od ręki nie liczy się do kolejki przed statusem Produkcja
Zabrze/Czekanów" bez zmiany kodu — domyślnie włączony (True), zgodnie z
zachowaniem wdrożonym w poprzedniej migracji logiki importu.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pawilony", "0006_welding_workers_seven"),
    ]

    operations = [
        migrations.AddField(
            model_name="capacityconfiguration",
            name="exclude_od_reki_before_production",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Gdy włączone: pawilony o Rodzaju 'Od ręki' nie liczą się do "
                    "kolejki, dopóki nie mają statusu Produkcja Zabrze albo "
                    "Produkcja Czekanów (samo Logistyka ich jeszcze nie liczy). "
                    "Wyłącz, żeby wrócić do liczenia 'Od ręki' na każdym aktywnym "
                    "statusie, tak jak 'Zamówiony'."
                ),
                verbose_name="Wyklucz 'Od ręki' z kolejki przed statusem produkcji",
            ),
        ),
    ]
