from django.contrib import admin

from pawilony.models import (
    CapacityConfiguration,
    ImportBatch,
    ManualBacklogAdjustment,
    OperationTime,
    PavilionSnapshot,
    Proforma,
    Reservation,
    WorkCenter,
)


@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "code")


@admin.register(OperationTime)
class OperationTimeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "work_center", "hours", "affects_term", "is_active", "updated_at")
    list_editable = ("hours", "is_active")
    list_filter = ("work_center", "affects_term", "is_active")


@admin.register(CapacityConfiguration)
class CapacityConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "general_units_per_week",
        "hydraulic_workers",
        "welding_workers",
        "fibo_wood_workers",
        "hours_per_worker_week",
        "safety_buffer_percent",
        "updated_at",
    )
    list_editable = ("is_active",)
    readonly_fields = (
        "effective_general_capacity",
        "effective_hydraulic_capacity_hours",
        "effective_welding_capacity_hours",
        "effective_fibo_wood_capacity_hours",
    )


@admin.register(ManualBacklogAdjustment)
class ManualBacklogAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("work_center_code", "hours", "is_active", "author", "created_at")
    list_editable = ("is_active",)
    list_filter = ("work_center_code", "is_active")

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class PavilionSnapshotInline(admin.TabularInline):
    model = PavilionSnapshot
    extra = 0
    fields = ("kod", "nazwa", "status_classification", "is_counted", "is_custom")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "uploaded_by",
        "uploaded_at",
        "status",
        "is_active_snapshot",
        "committed_at",
    )
    list_filter = ("status", "is_active_snapshot")
    readonly_fields = ("report", "uploaded_at", "committed_at")

    def has_add_permission(self, request):
        return False


@admin.register(PavilionSnapshot)
class PavilionSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "kod",
        "nazwa",
        "import_batch",
        "status_classification",
        "is_counted",
        "is_custom",
        "hydraulic_hours",
        "welding_hours",
        "fibo_wood_hours",
    )
    list_filter = ("import_batch", "status_classification", "is_counted", "is_custom")
    search_fields = ("kod", "nazwa")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "calculated_week_number", "calculated_week_year", "created_at")


@admin.register(Proforma)
class ProformaAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation", "is_paid", "amount", "created_at")
