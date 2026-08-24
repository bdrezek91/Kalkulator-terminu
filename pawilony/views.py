import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from pawilony.forms import CalculatorForm, ImportUploadForm
from pawilony.models import CapacityConfiguration, ImportBatch, ManualBacklogAdjustment
from pawilony.services.capacity import (
    compute_backlog_totals,
    compute_equipment_breakdown,
    fibo_wood_columns_present,
    get_active_configuration,
    get_active_import_batch,
    manual_adjustment_totals,
    NoActiveConfigurationError,
)
from pawilony.services.hours import PavilionEquipment, calculate_hours
from pawilony.services.import_service import (
    ImportAnalysisError,
    analyze_workbook,
    commit_batch,
    report_to_dict,
)
from pawilony.services.week_calculation import BRIGADE_LABELS, calculate_earliest_week

logger = logging.getLogger("pawilony.audit")


def _client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "unknown")


def _rate_limited(request) -> bool:
    from django.conf import settings

    key = f"calc-rate:{_client_ip(request)}"
    count = cache.get(key, 0)
    if count >= settings.CALCULATOR_RATE_LIMIT_COUNT:
        return True
    cache.set(key, count + 1, timeout=settings.CALCULATOR_RATE_LIMIT_WINDOW_SECONDS)
    return False


class CalculatorView(View):
    template_name = "pawilony/calculator.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CalculatorForm()})

    def post(self, request):
        form = CalculatorForm(request.POST)
        context = {"form": form}

        if not form.is_valid():
            return render(request, self.template_name, context)

        if _rate_limited(request):
            messages.error(request, "Zbyt wiele żądań. Spróbuj ponownie za chwilę.")
            return render(request, self.template_name, context, status=429)

        try:
            config = get_active_configuration()
        except NoActiveConfigurationError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, context)

        cleaned = form.cleaned_data
        equipment = PavilionEquipment(
            kuchnia=cleaned.get("kuchnia") or None,
            kuchnia_count=cleaned.get("kuchnia_count") or 1,
            toaleta=cleaned.get("toaleta") or None,
            lazienka=cleaned.get("lazienka") or None,
            bathroom_count=cleaned.get("bathroom_count") or 1,
            prysznic=cleaned.get("prysznic", False),
            pelna_statyka=cleaned.get("pelna_statyka", False),
            kratownica=cleaned.get("kratownica", False),
            module_count=cleaned.get("module_count") or 1,
            fibo=cleaned.get("fibo", False),
            boazeria=cleaned.get("boazeria", False),
            stolarka_nst=cleaned.get("stolarka_nst", False),
            zaluzje_fasadowe=cleaned.get("zaluzje_fasadowe", False),
            rolety=cleaned.get("rolety", False),
        )
        hours_result = calculate_hours(equipment)

        active_batch = get_active_import_batch()
        backlog = compute_backlog_totals(active_batch)
        week_result = calculate_earliest_week(backlog, hours_result, config)

        fibo_present, boazeria_present = fibo_wood_columns_present(active_batch)
        manual_totals = manual_adjustment_totals()
        fibo_wood_may_be_understated = (
            not (fibo_present and boazeria_present) and manual_totals["FIBO_WOOD"] == 0
        )

        stale_threshold_hours = config.stale_data_warning_hours
        data_is_stale = True
        last_import_at = None
        if active_batch and active_batch.committed_at:
            last_import_at = active_batch.committed_at
            age = timezone.now() - active_batch.committed_at
            data_is_stale = age.total_seconds() > stale_threshold_hours * 3600

        brigade_rows = []
        for outcome in week_result.brigade_outcomes:
            brigade_rows.append(
                {
                    "key": outcome.key,
                    "label": BRIGADE_LABELS[outcome.key],
                    "weeks": outcome.weeks,
                    "required": outcome.required,
                    "is_bottleneck": outcome.key == week_result.bottleneck_key,
                    "current_backlog": outcome.current_backlog,
                    "effective_capacity": outcome.effective_capacity,
                }
            )

        bottleneck_label = BRIGADE_LABELS[week_result.bottleneck_key]

        context.update(
            {
                "result": week_result,
                "brigade_rows": brigade_rows,
                "hours_result": hours_result,
                "bottleneck_label": bottleneck_label,
                "no_active_import": active_batch is None,
                "last_import_at": last_import_at,
                "data_is_stale": data_is_stale,
                "stale_threshold_hours": stale_threshold_hours,
                "fibo_wood_may_be_understated": fibo_wood_may_be_understated,
            }
        )
        return render(request, self.template_name, context)


class BacklogSummaryView(View):
    """
    Publiczne, zagregowane podsumowanie obecnego obciążenia kolejki —
    wyjaśnia, z czego wynika wyznaczany termin. Pokazuje wyłącznie liczby
    wg typu wyposażenia, nigdy kodów/nazw/numerów projektów pawilonów.
    """

    template_name = "pawilony/backlog_summary.html"

    def get(self, request):
        active_batch = get_active_import_batch()
        backlog = compute_backlog_totals(active_batch)
        breakdown = compute_equipment_breakdown(active_batch)
        manual_totals = manual_adjustment_totals()
        fibo_present, boazeria_present = fibo_wood_columns_present(active_batch)

        try:
            config = get_active_configuration()
            stale_threshold_hours = config.stale_data_warning_hours
        except NoActiveConfigurationError:
            config = None
            stale_threshold_hours = None

        last_import_at = None
        data_is_stale = True
        if active_batch and active_batch.committed_at:
            last_import_at = active_batch.committed_at
            if stale_threshold_hours is not None:
                age = timezone.now() - active_batch.committed_at
                data_is_stale = age.total_seconds() > stale_threshold_hours * 3600

        context = {
            "backlog": backlog,
            "breakdown": breakdown,
            "manual_totals": manual_totals,
            "config": config,
            "no_active_import": active_batch is None,
            "last_import_at": last_import_at,
            "data_is_stale": data_is_stale,
            "stale_threshold_hours": stale_threshold_hours,
            "fibo_wood_may_be_understated": not (fibo_present and boazeria_present)
            and manual_totals["FIBO_WOOD"] == 0,
        }
        return render(request, self.template_name, context)


class DashboardView(LoginRequiredMixin, View):
    login_url = "pawilony:login"
    template_name = "pawilony/admin/dashboard.html"

    def get(self, request):
        active_batch = get_active_import_batch()
        backlog = compute_backlog_totals(active_batch)
        config = CapacityConfiguration.objects.filter(is_active=True).first()

        custom_count = standard_count = 0
        if active_batch:
            counted = active_batch.pavilions.filter(is_counted=True)
            custom_count = counted.filter(is_custom=True).count()
            standard_count = counted.filter(is_custom=False).count()

        context = {
            "active_batch": active_batch,
            "backlog": backlog,
            "config": config,
            "custom_count": custom_count,
            "standard_count": standard_count,
            "recent_batches": ImportBatch.objects.all()[:5],
            "manual_adjustments": ManualBacklogAdjustment.objects.filter(is_active=True),
        }
        return render(request, self.template_name, context)


class ImportHistoryView(LoginRequiredMixin, ListView):
    login_url = "pawilony:login"
    model = ImportBatch
    template_name = "pawilony/admin/import_history.html"
    context_object_name = "batches"
    paginate_by = 25


class ImportUploadView(LoginRequiredMixin, View):
    login_url = "pawilony:login"
    template_name = "pawilony/admin/import_upload.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ImportUploadForm()})

    def post(self, request):
        form = ImportUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded_file = form.cleaned_data["file"]
        batch = ImportBatch.objects.create(
            file=uploaded_file,
            original_filename=uploaded_file.name,
            uploaded_by=request.user,
            status=ImportBatch.Status.PENDING_VALIDATION,
        )

        try:
            config = get_active_configuration()
            exclude_od_reki = config.exclude_od_reki_before_production
        except NoActiveConfigurationError:
            exclude_od_reki = True

        try:
            batch.file.open("rb")
            report, records = analyze_workbook(batch.file, exclude_od_reki_before_production=exclude_od_reki)
            batch.file.close()
        except ImportAnalysisError as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.report = {"error": str(exc)}
            batch.save(update_fields=["status", "report"])
            logger.warning("Import nieudany: batch_id=%s błąd=%s użytkownik=%s", batch.pk, exc, request.user)
            messages.error(request, f"Import nie powiódł się: {exc}")
            return redirect("pawilony:import_upload")

        report_dict = report_to_dict(report)
        report_dict["records"] = records
        batch.report = report_dict
        batch.status = ImportBatch.Status.VALIDATED
        batch.save(update_fields=["report", "status"])
        logger.info(
            "Import zwalidowany: batch_id=%s użytkownik=%s wierszy=%s konfliktów=%s",
            batch.pk,
            request.user,
            report.total_rows,
            report.conflict_count,
        )
        return redirect("pawilony:import_preview", pk=batch.pk)


class ImportPreviewView(LoginRequiredMixin, View):
    login_url = "pawilony:login"
    template_name = "pawilony/admin/import_preview.html"

    def get(self, request, pk):
        batch = get_object_or_404(ImportBatch, pk=pk)
        report = batch.report or {}
        return render(request, self.template_name, {"batch": batch, "report": report})


class ImportConfirmView(LoginRequiredMixin, View):
    login_url = "pawilony:login"

    def post(self, request, pk):
        batch = get_object_or_404(ImportBatch, pk=pk)
        if batch.status != ImportBatch.Status.VALIDATED:
            messages.error(request, "Ten import nie jest gotowy do zatwierdzenia.")
            return redirect("pawilony:import_preview", pk=pk)

        records = (batch.report or {}).get("records", [])
        commit_batch(batch, records, request.user)
        messages.success(request, "Import został zatwierdzony i jest teraz aktywną migawką.")
        return redirect("pawilony:import_preview", pk=pk)


class ImportRejectView(LoginRequiredMixin, View):
    login_url = "pawilony:login"

    def post(self, request, pk):
        batch = get_object_or_404(ImportBatch, pk=pk)
        batch.status = ImportBatch.Status.REJECTED
        batch.save(update_fields=["status"])
        logger.info("Import odrzucony: batch_id=%s użytkownik=%s", batch.pk, request.user)
        messages.info(request, "Import został odrzucony.")
        return redirect("pawilony:import_history")
