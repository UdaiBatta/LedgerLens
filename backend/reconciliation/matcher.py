from decimal import Decimal

from django.db import transaction

from .models import EvidenceConnection, EvidenceMatchMethod, FinancialRecord, ReconciliationCase


class EvidenceMatcher:
    @transaction.atomic
    def build_connections(
        self,
        reconciliation_case: ReconciliationCase,
        records: list[FinancialRecord],
    ) -> list[EvidenceConnection]:
        reconciliation_case.evidence_connections.all().delete()
        connections = []

        for sequence_number, (source_record, destination_record) in enumerate(
            zip(records, records[1:]),
            start=1,
        ):
            method, confidence, rationale = self._match(source_record, destination_record)
            connections.append(
                EvidenceConnection.objects.create(
                    reconciliation_case=reconciliation_case,
                    source_record=source_record,
                    destination_record=destination_record,
                    sequence_number=sequence_number,
                    match_method=method,
                    confidence=confidence,
                    matching_reason=rationale["summary"],
                    rationale=rationale,
                    is_verified=confidence == Decimal("1.0000"),
                )
            )

        return connections

    def _match(
        self,
        source_record: FinancialRecord,
        destination_record: FinancialRecord,
    ) -> tuple[str, Decimal, dict]:
        linked_reference = destination_record.raw_payload.get("linked_reference")
        if linked_reference == source_record.external_record_id:
            return (
                EvidenceMatchMethod.EXACT_REFERENCE,
                Decimal("1.0000"),
                {
                    "summary": "The destination record contains the source record identifier.",
                    "matched_fields": ["linked_reference"],
                    "tolerance_minor": 0,
                },
            )

        if source_record.reference and source_record.reference == destination_record.reference:
            return (
                EvidenceMatchMethod.SOURCE_REFERENCE,
                Decimal("0.9500"),
                {
                    "summary": "Both records contain the same financial reference.",
                    "matched_fields": ["reference"],
                    "tolerance_minor": 0,
                },
            )

        time_difference = abs(destination_record.occurred_at - source_record.occurred_at)
        amount_difference = abs(destination_record.amount_minor - source_record.amount_minor)
        return (
            EvidenceMatchMethod.AMOUNT_AND_TIME,
            Decimal("0.7500"),
            {
                "summary": "The records were linked by amount and occurrence window.",
                "matched_fields": ["amount_minor", "occurred_at"],
                "amount_difference_minor": amount_difference,
                "time_difference_seconds": int(time_difference.total_seconds()),
            },
        )
