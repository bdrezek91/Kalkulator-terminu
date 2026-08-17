from decimal import Decimal

import pytest
from django.urls import reverse

from pawilony.models import ImportBatch, PavilionSnapshot
from pawilony.services.capacity import compute_equipment_breakdown

pytestmark = pytest.mark.django_db


def _make_batch(user):
    return ImportBatch.objects.create(
        file="dummy.xlsx",
        original_filename="a.xlsx",
        uploaded_by=user,
        status=ImportBatch.Status.COMMITTED,
        is_active_snapshot=True,
    )


def test_backlog_summary_page_loads_without_login(client):
    response = client.get(reverse("pawilony:backlog_summary"))
    assert response.status_code == 200
    assert "Obciążenie kolejki" in response.content.decode()


def test_backlog_summary_does_not_leak_project_codes(client, django_user_model):
    user = django_user_model.objects.create_user(username="admin", password="secret123")
    batch = _make_batch(user)
    PavilionSnapshot.objects.create(
        import_batch=batch,
        kod="TAJNY-KOD-999",
        nazwa="Pawilon sekretny nr projektu 999/99/2099",
        status_classification="ACTIVE",
        is_counted=True,
        kuchnia="Lux",
        hydraulic_hours=Decimal("10"),
    )
    response = client.get(reverse("pawilony:backlog_summary"))
    body = response.content.decode()
    assert "TAJNY-KOD-999" not in body
    assert "999/99/2099" not in body
    assert "Lux" in body  # zagregowany typ wyposażenia jest OK


def test_equipment_breakdown_counts_by_variant(django_user_model):
    user = django_user_model.objects.create_user(username="admin2", password="secret123")
    batch = _make_batch(user)
    PavilionSnapshot.objects.create(
        import_batch=batch, kod="K1", status_classification="ACTIVE", is_counted=True,
        kuchnia="Standard", is_custom=True,
    )
    PavilionSnapshot.objects.create(
        import_batch=batch, kod="K2", status_classification="ACTIVE", is_counted=True,
        kuchnia="Lux", is_custom=True,
    )
    PavilionSnapshot.objects.create(
        import_batch=batch, kod="K3", status_classification="ACTIVE", is_counted=True,
        is_custom=False,
    )
    breakdown = compute_equipment_breakdown(batch)
    assert breakdown.total_counted == 3
    assert breakdown.standard_count == 1
    assert breakdown.custom_count == 2
    assert breakdown.kuchnia == {"Standard": 1, "Lux": 1}


def test_equipment_breakdown_excludes_toaleta_and_prysznic_when_lazienka_present(django_user_model):
    user = django_user_model.objects.create_user(username="admin3", password="secret123")
    batch = _make_batch(user)
    # łazienka jest kompletem — toaleta/prysznic nie powinny być liczone jako obciążające
    PavilionSnapshot.objects.create(
        import_batch=batch, kod="K1", status_classification="ACTIVE", is_counted=True,
        lazienka="Standard", toaleta="Premium", prysznic=True,
    )
    PavilionSnapshot.objects.create(
        import_batch=batch, kod="K2", status_classification="ACTIVE", is_counted=True,
        toaleta="Komfort",
    )
    breakdown = compute_equipment_breakdown(batch)
    assert breakdown.lazienka == {"Standard": 1}
    assert breakdown.toaleta == {"Komfort": 1}
    assert breakdown.prysznic_count == 0


def test_equipment_breakdown_no_active_batch_returns_empty():
    breakdown = compute_equipment_breakdown(None)
    assert breakdown.total_counted == 0
    assert breakdown.kuchnia == {}
