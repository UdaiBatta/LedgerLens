from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db import transaction

from .models import EvidenceConnection, EvidenceMatchMethod


class EvidenceMatcher:
    predecessor_types = {
        "payment": {"order"}, "fee": {"payment"}, "tax": {"fee"},
        "refund": {"payment"}, "settlement": {"payment", "fee", "tax", "refund"},
        "bank_credit": {"settlement"}, "ledger_entry": {"bank_credit"},
    }

    def decisions(self, records, tolerance_minor=0, window_seconds=259200):
        """Candidates are review evidence, never authoritative matching decisions."""
        decisions = []
        for destination in records:
            allowed = [r for r in records if r.pk != destination.pk
                       and r.source.organization_id == destination.source.organization_id
                       and r.entity_id == destination.entity_id
                       and r.currency == destination.currency
                       and r.record_type in self.predecessor_types.get(destination.record_type, set())]
            references = destination.raw_payload.get("contributing_references", [])
            if not isinstance(references, list) or not all(isinstance(ref, str) for ref in references):
                raise ValidationError("contributing_references must be a list of record identifiers.")
            references = list(dict.fromkeys(references + [destination.reference or destination.raw_payload.get("linked_reference", "")]))
            explicit = [r for r in allowed if r.external_record_id in references]
            ambiguous_reference = any(sum(r.external_record_id == ref for r in explicit) > 1 for ref in references if ref)
            if explicit:
                candidates = explicit
                state = "ambiguous" if ambiguous_reference else "confirmed"
                method = EvidenceMatchMethod.EXACT_REFERENCE
            else:
                candidates = [r for r in allowed
                              if abs(r.amount_minor - destination.amount_minor) <= tolerance_minor
                              and abs((r.occurred_at - destination.occurred_at).total_seconds()) <= window_seconds]
                state = "ambiguous" if len(candidates) > 1 else "candidate" if candidates else "missing"
                method = EvidenceMatchMethod.AMOUNT_AND_TIME
            if destination.record_type == "order":
                continue
            decisions.append({"destination_id": destination.pk, "state": state,
                              "candidate_ids": [r.pk for r in candidates], "method": method,
                              "matched_fields": ["reference"] if explicit else ["amount_minor", "occurred_at"],
                              "tolerance_minor": tolerance_minor, "window_seconds": window_seconds})
        return decisions

    @transaction.atomic
    def build_connections(self, reconciliation_case, records, decisions=None):
        if any(r.source.organization_id != reconciliation_case.organization_id for r in records):
            raise ValidationError("Evidence must belong to the case organization.")
        decisions = decisions if decisions is not None else self.decisions(records)
        by_id = {r.pk: r for r in records}
        # Latest projection only; immutable reconciliation runs retain earlier decisions.
        reconciliation_case.evidence_connections.all().delete()
        connections = []
        for decision in decisions:
            for source_id in decision["candidate_ids"]:
                confirmed = decision["state"] == "confirmed"
                connections.append(EvidenceConnection.objects.create(
                    reconciliation_case=reconciliation_case,
                    source_record=by_id[source_id], destination_record=by_id[decision["destination_id"]],
                    sequence_number=len(connections) + 1, match_method=decision["method"],
                    confidence=Decimal("1.0000") if confirmed else Decimal("0.7500"),
                    matching_reason="Explicit reference." if confirmed else "Candidate requires human verification.",
                    rationale=decision, is_verified=confirmed,
                ))
        return connections
