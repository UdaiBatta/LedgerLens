from dataclasses import asdict, dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .immutability import content_digest
from .matcher import EvidenceMatcher
from .models import (AuditEvent, CheckResult, FinancialRecord, ReconciliationCase,
                     ReconciliationRuleVersion, ReconciliationRun)


@dataclass(frozen=True)
class RuleOutcome:
    name: str
    result: str
    evidence: list[str]
    details: str
    expected_minor: int | None = None
    actual_minor: int | None = None
    classification: str = ""
    first_break_id: int | None = None


class ReconciliationEngine:
    """One explicitly selected settlement scope, single currency, no FX or implicit allocations."""

    @transaction.atomic
    def reconcile(self, organization, case_reference, entity_id, records, *, as_of=None):
        as_of = as_of or timezone.now()
        if timezone.is_naive(as_of):
            raise ValidationError("as_of must include a timezone.")
        ids = [r.pk for r in records]
        if not ids or None in ids or len(ids) != len(set(ids)):
            raise ValidationError("Supply distinct persisted financial records.")
        if len(ids) > 10000:
            raise ValidationError("This synchronous scope is limited to 10,000 records.")
        # Re-read persisted truth, not possibly modified in-memory model instances.
        records = list(FinancialRecord.objects.filter(pk__in=ids).select_related("source").order_by("occurred_at", "id"))
        if len(records) != len(ids) or any(r.source.organization_id != organization.pk or r.entity_id != entity_id for r in records):
            raise ValidationError("Every record must belong to the requested organization and scope.")
        if len({r.currency for r in records}) != 1:
            raise ValidationError("Mixed currencies require an explicit FX workflow.")
        if any(r.ingested_at > as_of for r in records):
            raise ValidationError("The scope includes evidence received after as_of.")
        payments = [r for r in records if r.record_type == "payment"]
        if not payments:
            raise ValidationError("At least one payment record is required.")
        # Serializes runs and case projection updates within an organization.
        type(organization).objects.select_for_update().get(pk=organization.pk)
        rules = list(ReconciliationRuleVersion.objects.filter(source_id__in={p.source_id for p in payments}, currency=records[0].currency))
        selected = {}
        checks = []
        for payment in payments:
            applicable = [rule for rule in rules if rule.source_id == payment.source_id
                          and rule.effective_from <= payment.occurred_at
                          and (rule.effective_until is None or payment.occurred_at < rule.effective_until)]
            if len(applicable) != 1:
                checks.append(RuleOutcome("Commercial rule selection", "waiting", [payment.external_record_id],
                                          "Exactly one effective source/currency rule is required.", classification="rule_missing_or_ambiguous", first_break_id=payment.pk))
            else:
                selected[payment.pk] = applicable[0]
        matcher = EvidenceMatcher()
        decisions = matcher.decisions(records)
        if not checks:
            checks = self._checks(records, payments, selected, decisions, as_of)
        failed = next((check for check in checks if check.result == "failed"), None)
        waiting = next((check for check in checks if check.result == "waiting"), None)
        first = failed or waiting
        final = checks[-1]
        result = {
            "entity_id": entity_id, "currency": records[0].currency,
            "exception_type": first.classification if first else "clean_match",
            "status": "needs_review" if failed else "insufficient_evidence" if waiting else "matched",
            "expected_amount_minor": (first.expected_minor if first else final.expected_minor) or 0,
            "actual_amount_minor": (first.actual_minor if first else final.actual_minor) or 0,
            "first_break_record_id": first.first_break_id if first else None,
            "amounts_known": not first or (first.result == "failed" and first.expected_minor is not None and first.actual_minor is not None),
        }
        result["difference_minor"] = result["actual_amount_minor"] - result["expected_amount_minor"] if result["amounts_known"] else None
        previous = ReconciliationCase.objects.filter(organization=organization, case_reference=case_reference).first()
        if previous and previous.entity_id != entity_id:
            raise ValidationError("A case reference cannot be reassigned to a different scope.")
        before = {"status": previous.status, "exception_type": previous.exception_type} if previous else {}
        case, created = ReconciliationCase.objects.update_or_create(
            organization=organization, case_reference=case_reference,
            defaults={key: value for key, value in result.items() if key not in {"amounts_known", "difference_minor"}},
        )
        case.check_results.all().delete()
        for check in checks:
            CheckResult.objects.create(reconciliation_case=case, check_name=check.name[:120],
                                       result=check.result, evidence=check.evidence, details=check.details[:500])
        matcher.build_connections(case, records, decisions)
        inputs = [self.snapshot(record) for record in records]
        rule_snapshots = [self.snapshot(rule) for rule in {rule.pk: rule for rule in selected.values()}.values()]
        watermarks = {}
        for record in records:
            key = str(record.source_id)
            watermarks[key] = max(watermarks.get(key, ""), record.ingested_at.isoformat())
        run = ReconciliationRun.objects.create(
            reconciliation_case=case, as_of=as_of, inputs=inputs, rules=rule_snapshots,
            decisions=decisions, checks=[asdict(check) for check in checks], result=result,
            source_watermarks=watermarks, input_hash=content_digest({"inputs": inputs, "rules": rule_snapshots, "as_of": as_of.isoformat()}),
        )
        AuditEvent.objects.create(organization=organization, reconciliation_case=case,
                                  event_type="case_created" if created else "reconciliation_completed",
                                  before=before, after={"run_id": str(run.public_id), **result}, correlation_id=run.public_id)
        return case

    def _checks(self, records, payments, rules, decisions, as_of):
        checks = []
        by_type = {}
        for record in records:
            by_type.setdefault(record.record_type, []).append(record)
        settlements = by_type.get("settlement", [])
        banks = by_type.get("bank_credit", [])
        ledgers = by_type.get("ledger_entry", [])
        if len(settlements) > 1 or len({p.source_id for p in payments}) > 1:
            return [RuleOutcome("Scope allocation", "waiting", self._references(*records),
                                "Multiple settlements or payment providers require explicit allocations; this scope is blocked.",
                                classification="unsupported_allocation")]
        if any(r.status not in {"processed", "captured", "posted", "settled"} for r in records):
            return [RuleOutcome("Lifecycle eligibility", "waiting", self._references(*records),
                                "Only final captured/processed/posted/settled events are supported.",
                                classification="unsupported_lifecycle")]
        if any(r.direction != ("debit" if r.record_type in {"fee", "tax", "refund"} else "credit") for r in records):
            return [RuleOutcome("Direction eligibility", "waiting", self._references(*records),
                                "Reversals and other posting directions require an explicit lifecycle adapter.",
                                classification="unsupported_direction")]
        ambiguous = [d for d in decisions if d["state"] == "ambiguous"]
        if ambiguous:
            return [RuleOutcome("Evidence identity", "waiting", self._references(*records),
                                "Multiple candidates satisfy a reference or amount rule; human resolution is required.",
                                classification="ambiguous_match")]
        total_fee = total_tax = 0
        captured = sum(p.amount_minor for p in payments)
        for payment in payments:
            rule = rules[payment.pk]
            fee = self._linked(by_type.get("fee", []), payment)
            tax = self._linked(by_type.get("tax", []), fee) if fee else None
            orders = [r for r in by_type.get("order", []) if r.external_record_id == payment.reference]
            order = orders[0] if len(orders) == 1 else None
            expected_fee = self._apply_basis_points(payment.amount_minor, rule.fee_basis_points)
            expected_tax = self._apply_basis_points(expected_fee, rule.tax_basis_points)
            total_fee += expected_fee
            total_tax += expected_tax
            suffix = "" if len(payments) == 1 else f" ({payment.external_record_id})"
            checks += [
                self.compare("Order amount matches capture" + suffix, order.amount_minor if order else None, payment.amount_minor, [order, payment], "order_mismatch"),
                self.compare("Processing fee calculation" + suffix, expected_fee, fee.amount_minor if fee else None, [payment, fee], "fee_mismatch", rule.tolerance_minor),
                self.compare("Tax on fee calculation" + suffix, expected_tax, tax.amount_minor if tax else None, [fee, tax], "tax_mismatch", rule.tolerance_minor),
            ]
        refunds = by_type.get("refund", [])
        refund_total = 0
        for payment in payments:
            linked = [r for r in refunds if r.reference == payment.external_record_id]
            refunded = sum(r.amount_minor for r in linked)
            checks.append(RuleOutcome("Refund limit (" + payment.external_record_id + ")", "passed" if refunded <= payment.amount_minor else "failed",
                                      self._references(payment, *linked), "Processed refunds cannot exceed the capture.",
                                      payment.amount_minor, refunded, "refund_exceeds_capture", linked[-1].pk if linked else payment.pk))
            if rules[payment.pk].refund_policy == "deduct_processed":
                refund_total += refunded
        if any(r.reference not in {p.external_record_id for p in payments} for r in refunds):
            checks.append(RuleOutcome("Refund relationship", "waiting", self._references(*refunds),
                                      "Refunds must explicitly identify a capture.", classification="refund_reference_missing"))
        expected = captured - total_fee - total_tax - refund_total
        if expected < 0:
            return checks + [RuleOutcome("Net settlement eligibility", "waiting", self._references(*records),
                                         "A negative net obligation needs an explicit bank-debit settlement workflow.",
                                         classification="unsupported_negative_settlement")]
        settlement = settlements[0] if settlements else None
        due = max(p.occurred_at + timedelta(hours=rules[p.pk].settlement_wait_hours) for p in payments)
        checks.append(self.compare("Settlement amount calculation", expected, settlement.amount_minor if settlement else None,
                                   payments + refunds + settlements, "settlement_mismatch",
                                   missing="settlement_overdue" if as_of > due else "settlement_not_yet_due"))
        bank_total = sum(r.amount_minor for r in banks) if banks else None
        bank_verified = bool(settlement and banks and all(r.reference == settlement.external_record_id for r in banks))
        bank_due = settlement.occurred_at + timedelta(hours=max(rule.bank_wait_hours for rule in rules.values())) if settlement else due
        checks.append(self.compare("Bank credit equals settlement", settlement.amount_minor if settlement else None, bank_total,
                                   settlements + banks, "settlement_short",
                                   missing="bank_credit_overdue" if as_of > bank_due else "bank_credit_not_yet_due"))
        if banks and settlement and not bank_verified:
            checks[-1] = RuleOutcome("Bank credit equals settlement", "waiting", self._references(settlement, *banks),
                                     "Candidate bank receipts lack an explicit settlement reference; comparison requires confirmation.",
                                     settlement.amount_minor, bank_total, "unverified_bank_relationship", banks[0].pk)
        ledger_total = sum(r.amount_minor for r in ledgers) if ledgers else None
        checks.append(self.compare("Bank credit equals general ledger", bank_total, ledger_total, banks + ledgers, "ledger_mismatch", missing="ledger_posting_missing"))
        for bank in banks:
            postings = [r for r in ledgers if r.reference == bank.external_record_id]
            checks.append(self.compare("Ledger receipt (" + bank.external_record_id + ")", bank.amount_minor,
                                       sum(r.amount_minor for r in postings) if postings else None,
                                       [bank] + postings, "ledger_mismatch", missing="ledger_posting_missing"))
        if settlement:
            ancestors = {settlement.pk}
            edges = [(source, d["destination_id"]) for d in decisions if d["state"] == "confirmed" for source in d["candidate_ids"]]
            while True:
                expanded = ancestors | {source for source, destination in edges if destination in ancestors}
                if expanded == ancestors:
                    break
                ancestors = expanded
            required_ids = {r.pk for r in records if r.record_type in {"payment", "fee", "tax"}}
            if not required_ids <= ancestors:
                checks.append(RuleOutcome("Settlement membership", "waiting", self._references(*payments, settlement),
                                          "The settlement does not explicitly account for every capture and deduction.",
                                          classification="settlement_membership_missing"))
        # Even a unique fuzzy candidate cannot certify a financial relationship.
        unresolved = [d for d in decisions if d["state"] != "confirmed"]
        if unresolved:
            checks.append(RuleOutcome("Evidence relationships", "waiting", self._references(*records),
                                      "Some relationships are missing or inferred; confirm source references.",
                                      classification="unverified_relationship"))
        # The final control total is used only when every mandatory check passes.
        checks.append(self.compare("End-to-end control total", expected if bank_verified else None, ledger_total, payments + ledgers, "control_total_mismatch"))
        return checks

    @staticmethod
    def compare(name, expected, actual, records, classification, tolerance=0, missing="waiting_for_evidence"):
        available = [r for r in records if r]
        state = "waiting" if expected is None or actual is None else "passed" if abs(expected - actual) <= tolerance else "failed"
        return RuleOutcome(name, state, [r.external_record_id for r in available],
                           f"Expected {expected}; observed {actual}; tolerance {tolerance} minor units.",
                           expected, actual, missing if state == "waiting" else classification,
                           available[-1].pk if available else None)

    @staticmethod
    def _linked(candidates, predecessor):
        linked = [r for r in candidates if r.reference == predecessor.external_record_id]
        return linked[0] if len(linked) == 1 else None

    @staticmethod
    def snapshot(record):
        return {field.attname: (value.isoformat() if hasattr(value, "isoformat") else str(value) if field.get_internal_type() == "UUIDField" else value)
                for field in record._meta.concrete_fields for value in [getattr(record, field.attname)]}

    @staticmethod
    def _apply_basis_points(amount_minor, basis_points):
        return (amount_minor * basis_points + 5000) // 10000

    @staticmethod
    def _references(*records):
        return [r.external_record_id for r in records if r]
