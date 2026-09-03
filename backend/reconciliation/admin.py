from django.contrib import admin

from .models import (
    EvidenceConnection,
    FinancialDataSource,
    FinancialRecord,
    Organization,
    ReconciliationCase,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(FinancialDataSource)
class FinancialDataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "source_type", "created_at")
    list_filter = ("source_type",)
    search_fields = ("name", "organization__name", "external_account_reference")


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
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


@admin.register(ReconciliationCase)
class ReconciliationCaseAdmin(admin.ModelAdmin):
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
class EvidenceConnectionAdmin(admin.ModelAdmin):
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
