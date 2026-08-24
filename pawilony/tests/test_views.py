import io

import openpyxl
import pytest
from django.urls import reverse

from pawilony.models import ImportBatch, PavilionSnapshot

pytestmark = pytest.mark.django_db


def test_calculator_page_loads(client):
    response = client.get(reverse("pawilony:calculator"))
    assert response.status_code == 200
    assert "Kalkulator terminu pawilonu" in response.content.decode()


def test_calculator_computes_result(client, operation_times, active_config):
    response = client.post(
        reverse("pawilony:calculator"),
        {"kuchnia": "Standard", "pelna_statyka": "on"},
    )
    assert response.status_code == 200
    assert "Wynik" in response.content.decode() or "wynik" in response.content.decode().lower()


def test_calculator_rejects_statyka_and_kratownica_together(client, operation_times, active_config):
    response = client.post(
        reverse("pawilony:calculator"),
        {"pelna_statyka": "on", "kratownica": "on"},
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "wyklucz" in body.lower()
    assert "Wynik" not in body


def test_admin_panel_requires_login(client):
    response = client.get(reverse("pawilony:dashboard"))
    assert response.status_code == 302
    assert "/admin-panel/login/" in response.url


def test_import_upload_requires_login(client):
    response = client.get(reverse("pawilony:import_upload"))
    assert response.status_code == 302


def test_admin_panel_accessible_after_login(client, django_user_model):
    django_user_model.objects.create_user(username="admin", password="secret123")
    client.login(username="admin", password="secret123")
    response = client.get(reverse("pawilony:dashboard"))
    assert response.status_code == 200


def test_public_calculator_does_not_leak_project_codes(client, operation_times, active_config, django_user_model):
    user = django_user_model.objects.create_user(username="admin2", password="secret123")
    batch = ImportBatch.objects.create(
        file="dummy.xlsx", original_filename="a.xlsx", uploaded_by=user,
        status=ImportBatch.Status.COMMITTED, is_active_snapshot=True,
    )
    PavilionSnapshot.objects.create(
        import_batch=batch,
        kod="TAJNY-KOD-PROJEKTU-999",
        nazwa="Pawilon sekretny nr projektu 999/99/2099",
        status_classification="ACTIVE",
        is_counted=True,
    )
    response = client.post(reverse("pawilony:calculator"), {"kuchnia": "Standard"})
    body = response.content.decode()
    assert "TAJNY-KOD-PROJEKTU-999" not in body
    assert "999/99/2099" not in body


def test_import_upload_flow(client, django_user_model, operation_times):
    user = django_user_model.objects.create_user(username="admin3", password="secret123")
    client.login(username="admin3", password="secret123")

    header = [
        "Kod", "Nazwa", "Typ", "Stan zasobów", "Ilość dostępna", "Jm",
        "01. ODDZIAŁ (Atrybut)", "02. RODZAJ (Atrybut)", "03. STATUS PROCESU (Atrybut)",
        "07. TERMIN REALIZ. (Atrybut)", "23. PŁYTY NIESTANDAR (Atrybut)",
        "25. PEŁNA/STATYKA (Atrybut)", "24. KRATOWNICA (Atrybut)", "26. KUCHNIA (Atrybut)",
        "28. PRYSZNIC (Atrybut)", "27. TOALETA (Atrybut)", "30. STOLARKA NST (Atrybut)",
        "32. ŻALUZJE FASADOWE (Atrybut)", "31. ROLETY (Atrybut)", "34. ŁAZIENKA (Atrybut)",
        "33. INNE NIESTANDARD (Atrybut)",
    ]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lista zasobów"
    ws.append(header)
    ws.append(["K1", "Pawilon testowy", "TZ", "Brak towaru", 1, "szt", "Zabrze", "Zamówiony", "Logistyka"] + [""] * 12)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = "test_import.xlsx"

    response = client.post(reverse("pawilony:import_upload"), {"file": buf}, format="multipart")
    assert response.status_code == 302
    batch = ImportBatch.objects.latest("uploaded_at")
    assert batch.status == ImportBatch.Status.VALIDATED

    response = client.get(reverse("pawilony:import_preview", kwargs={"pk": batch.pk}))
    assert response.status_code == 200

    response = client.post(reverse("pawilony:import_confirm", kwargs={"pk": batch.pk}))
    assert response.status_code == 302
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.COMMITTED
    assert batch.is_active_snapshot is True
    assert PavilionSnapshot.objects.filter(import_batch=batch, is_counted=True).count() == 1


def test_import_upload_honors_od_reki_toggle(client, django_user_model, operation_times, active_config):
    active_config.exclude_od_reki_before_production = False
    active_config.save(update_fields=["exclude_od_reki_before_production"])

    user = django_user_model.objects.create_user(username="admin4", password="secret123")
    client.login(username="admin4", password="secret123")

    header = [
        "Kod", "Nazwa", "Typ", "Stan zasobów", "Ilość dostępna", "Jm",
        "01. ODDZIAŁ (Atrybut)", "02. RODZAJ (Atrybut)", "03. STATUS PROCESU (Atrybut)",
        "07. TERMIN REALIZ. (Atrybut)", "23. PŁYTY NIESTANDAR (Atrybut)",
        "25. PEŁNA/STATYKA (Atrybut)", "24. KRATOWNICA (Atrybut)", "26. KUCHNIA (Atrybut)",
        "28. PRYSZNIC (Atrybut)", "27. TOALETA (Atrybut)", "30. STOLARKA NST (Atrybut)",
        "32. ŻALUZJE FASADOWE (Atrybut)", "31. ROLETY (Atrybut)", "34. ŁAZIENKA (Atrybut)",
        "33. INNE NIESTANDARD (Atrybut)",
    ]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lista zasobów"
    ws.append(header)
    # "Od ręki" na Logistyce — z wyłączonym przełącznikiem powinno się liczyć.
    ws.append(["K1", "Pawilon testowy", "TZ", "Brak towaru", 1, "szt", "Zabrze", "Od ręki", "Logistyka"] + [""] * 12)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = "test_import.xlsx"

    response = client.post(reverse("pawilony:import_upload"), {"file": buf}, format="multipart")
    assert response.status_code == 302
    batch = ImportBatch.objects.latest("uploaded_at")
    assert batch.report["od_reki_excluded_count"] == 0
    assert batch.report["records"][0]["is_counted"] is True
