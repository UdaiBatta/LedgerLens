from rest_framework import serializers

from .models import AgentRun, CheckResult, EvidenceConnection, FinancialRecord, ReconciliationCase


class FinancialRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = FinancialRecord
        fields = (
            "id",
            "external_record_id",
            "record_type",
            "entity_id",
            "amount_minor",
            "fee_minor",
            "tax_minor",
            "currency",
            "occurred_at",
            "status",
            "reference",
            "source_name",
            "raw_payload",
        )


class CheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckResult
        fields = ("check_name", "result", "evidence", "details", "ran_at")


class EvidenceConnectionSerializer(serializers.ModelSerializer):
    source = FinancialRecordSerializer(source="source_record", read_only=True)
    destination = FinancialRecordSerializer(source="destination_record", read_only=True)

    class Meta:
        model = EvidenceConnection
        fields = (
            "sequence_number",
            "link_type",
            "match_method",
            "confidence",
            "rationale",
            "created_by",
            "is_verified",
            "source",
            "destination",
        )


class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = (
            "id",
            "question",
            "tool_calls",
            "conclusion",
            "recommended_action",
            "confidence",
            "evidence_cited",
            "sufficient_evidence",
            "model_version",
            "created_at",
        )


class ReconciliationCaseListSerializer(serializers.ModelSerializer):
    difference_minor = serializers.IntegerField(read_only=True)

    class Meta:
        model = ReconciliationCase
        fields = (
            "public_id",
            "case_reference",
            "entity_id",
            "exception_type",
            "status",
            "currency",
            "expected_amount_minor",
            "actual_amount_minor",
            "difference_minor",
            "owner",
            "opened_at",
        )


class ReconciliationCaseDetailSerializer(ReconciliationCaseListSerializer):
    first_break_record = FinancialRecordSerializer(read_only=True)
    check_results = CheckResultSerializer(many=True, read_only=True)
    evidence_connections = EvidenceConnectionSerializer(many=True, read_only=True)
    agent_runs = AgentRunSerializer(many=True, read_only=True)

    class Meta(ReconciliationCaseListSerializer.Meta):
        fields = ReconciliationCaseListSerializer.Meta.fields + (
            "first_break_record",
            "check_results",
            "evidence_connections",
            "agent_runs",
        )
