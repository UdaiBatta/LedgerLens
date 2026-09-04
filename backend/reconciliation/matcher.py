from decimal import Decimal

from django.db import transaction

from .models import EvidenceConnection, EvidenceMatchMethod, FinancialRecord, ReconciliationCase


class EvidenceMatcher:
    fuzzy_time_window_seconds = 3 * 24 * 60 * 60
    minimum_amount_tolerance_minor = 1_000
    predecessor_types = {
        "payment": {"order"},
        "fee": {"payment"},
        "tax": {"fee"},
        "refund": {"payment"},
        "settlement": {"payment", "fee", "tax", "refund"},
        "bank_credit": {"settlement"},
        "ledger_entry": {"bank_credit"},
    }

    @transaction.atomic
    def build_connections(
        self,
        reconciliation_case: ReconciliationCase,
        records: list[FinancialRecord],
    ) -> list[EvidenceConnection]:
        reconciliation_case.evidence_connections.all().delete()
        connections = []

        ordered_records = sorted(records, key=lambda record: (record.occurred_at, record.id))
        records_by_external_id = {
            record.external_record_id: record for record in ordered_records
        }
        matched_pairs = []
        for destination_index, destination_record in enumerate(ordered_records[1:], start=1):
            prior_records = ordered_records[:destination_index]
            linked_reference = (
                destination_record.reference
                or destination_record.raw_payload.get("linked_reference", "")
            )
            source_record = records_by_external_id.get(linked_reference)
            if source_record not in prior_records:
                source_record = None
            if not source_record:
                source_record = self._closest_allowed_predecessor(
                    prior_records,
                    destination_record,
                )
            if source_record:
                matched_pairs.append((source_record, destination_record))

        for sequence_number, (source_record, destination_record) in enumerate(
            matched_pairs,
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

    def _closest_allowed_predecessor(self, candidates, destination_record):
        allowed_types = self.predecessor_types.get(destination_record.record_type, set())
        eligible_candidates = []
        for candidate in candidates:
            time_difference = abs(destination_record.occurred_at - candidate.occurred_at)
            amount_difference = abs(destination_record.amount_minor - candidate.amount_minor)
            amount_tolerance = max(
                self.minimum_amount_tolerance_minor,
                destination_record.amount_minor * 2 // 100,
            )
            if (
                candidate.record_type in allowed_types
                and candidate.currency == destination_record.currency
                and time_difference.total_seconds() <= self.fuzzy_time_window_seconds
                and amount_difference <= amount_tolerance
            ):
                eligible_candidates.append(
                    (amount_difference, time_difference, candidate.id, candidate)
                )
        if not eligible_candidates:
            return None
        return min(eligible_candidates, key=lambda match: match[:3])[3]

    def _match(
        self,
        source_record: FinancialRecord,
        destination_record: FinancialRecord,
    ) -> tuple[str, Decimal, dict]:
        linked_reference = (
            destination_record.reference
            or destination_record.raw_payload.get("linked_reference")
        )
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
                "amount_tolerance_minor": max(
                    self.minimum_amount_tolerance_minor,
                    destination_record.amount_minor * 2 // 100,
                ),
                "time_window_seconds": self.fuzzy_time_window_seconds,
            },
        )
