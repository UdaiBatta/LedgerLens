from django.contrib import admin

from .models import (
    AgentRun,
    CheckResult,
    EvidenceConnection,
    FinancialDataSource,
    FinancialRecord,
    IngestionBatch,
    Organization,
    OrganizationMembership,
    ReconciliationRuleVersion,
    ReconciliationRun,
    AuditEvent,
    IngestionDelivery,
    ReconciliationCase,
)


class ReadOnlyEvidenceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(FinancialDataSource)
class FinancialDataSourceAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return ("organization", "source_type", "external_account_reference") if obj else ()

    list_display = ("name", "organization", "source_type", "created_at")
    list_filter = ("source_type",)
    search_fields = ("name", "organization__name", "external_account_reference")


@admin.register(FinancialRecord)
class FinancialRecordAdmin(ReadOnlyEvidenceAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    list_display = (
        "external_record_id",
        "record_type",
        "source",
        "amount_minor",
        "currency",
        "occurred_at",
    )
    list_filter = ("record_type", "direction", "currency")
    search_fields = ("external_record_id", "source__name")


@admin.register(IngestionBatch)
class IngestionBatchAdmin(ReadOnlyEvidenceAdmin):
    list_display = (
        "batch_reference",
        "source",
        "status",
        "received_count",
        "imported_count",
        "duplicate_count",
        "rejected_count",
        "created_at",
    )
    list_filter = ("status", "source__source_type")
    search_fields = ("batch_reference", "source__name", "source__organization__name")


@admin.register(ReconciliationCase)
class ReconciliationCaseAdmin(ReadOnlyEvidenceAdmin):
    list_display = (
        "case_reference",
        "organization",
        "status",
        "difference_minor",
        "opened_at",
    )
    list_filter = ("status", "currency")
    search_fields = ("case_reference", "organization__name")


@admin.register(EvidenceConnection)
class EvidenceConnectionAdmin(ReadOnlyEvidenceAdmin):
    list_display = (
        "reconciliation_case",
        "sequence_number",
        "source_record",
        "destination_record",
        "match_method",
        "confidence",
        "is_verified",
    )
    list_filter = ("match_method", "is_verified")


@admin.register(CheckResult)
class CheckResultAdmin(ReadOnlyEvidenceAdmin):
    list_display = ("reconciliation_case", "check_name", "result", "ran_at")
    list_filter = ("result",)


@admin.register(AgentRun)
class AgentRunAdmin(ReadOnlyEvidenceAdmin):
    list_display = (
        "reconciliation_case",
        "confidence",
        "sufficient_evidence",
        "model_version",
        "created_at",
    )
    list_filter = ("sufficient_evidence", "model_version")


admin.site.register(OrganizationMembership)


class ImmutableControlAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(ReconciliationRuleVersion, ImmutableControlAdmin)
admin.site.register(ReconciliationRun, ReadOnlyEvidenceAdmin)
admin.site.register(AuditEvent, ReadOnlyEvidenceAdmin)
admin.site.register(IngestionDelivery, ReadOnlyEvidenceAdmin)
