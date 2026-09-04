from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from .matcher import EvidenceMatcher
from .models import (
    CheckResult,
    CheckResultStatus,
    FinancialRecord,
    FinancialRecordType,
    Organization,
    ReconciliationCase,
    ReconciliationStatus,
)


@dataclass(frozen=True)
class RuleOutcome:
    name: str
    result: str
    evidence: list[str]
    details: str


@dataclass(frozen=True)
class PaymentBreakdown:
    order: FinancialRecord | None
    payment: FinancialRecord
    fee: FinancialRecord | None
    tax: FinancialRecord | None
    captured_amount: int
    expected_fee: int
    expected_tax: int


class ReconciliationEngine:
    processing_fee_basis_points = 120
    tax_on_fee_basis_points = 1800

    @transaction.atomic
    def reconcile(
        self,
        organization: Organization,
        case_reference: str,
        entity_id: str,
        records: list[FinancialRecord],
    ) -> ReconciliationCase:
        ordered_records = sorted(records, key=lambda record: (record.occurred_at, record.id))
        if not ordered_records:
            raise ValidationError("At least one financial record is required.")
        if any(record.source.organization_id != organization.id for record in ordered_records):
            raise ValidationError("Every record must belong to the reconciliation organization.")
        if any(record.entity_id != entity_id for record in ordered_records):
            raise ValidationError("Every record must belong to the requested entity trace.")
        if len({record.currency for record in ordered_records}) != 1:
            raise ValidationError("A reconciliation trace cannot mix currencies.")
        payments = [
            record
            for record in ordered_records
            if record.record_type == FinancialRecordType.PAYMENT
        ]
        if not payments:
            raise ValidationError("At least one payment record is required.")
        settlement = self._first(ordered_records, FinancialRecordType.SETTLEMENT)
        bank_credit = self._first(ordered_records, FinancialRecordType.BANK_CREDIT)
        refunds = self._sum(ordered_records, FinancialRecordType.REFUND)

        payment_breakdowns = [
            self._payment_breakdown(payment, ordered_records, single_payment=len(payments) == 1)
            for payment in payments
        ]
        captured_amount = sum(breakdown.captured_amount for breakdown in payment_breakdowns)
        expected_fee_total = sum(breakdown.expected_fee for breakdown in payment_breakdowns)
        expected_tax_total = sum(breakdown.expected_tax for breakdown in payment_breakdowns)
        expected_settlement = captured_amount - refunds - expected_fee_total - expected_tax_total
        actual_amount = bank_credit.amount_minor if bank_credit else 0

        first_break, exception_type, status, first_break_expected, first_break_actual = self._classify(
            payments,
            payment_breakdowns,
            settlement,
            bank_credit,
            expected_settlement,
            actual_amount,
        )

        reconciliation_case, _ = ReconciliationCase.objects.update_or_create(
            organization=organization,
            case_reference=case_reference,
            defaults={
                "entity_id": entity_id,
                "exception_type": exception_type,
                "status": status,
                "currency": payments[0].currency,
                "expected_amount_minor": first_break_expected,
                "actual_amount_minor": first_break_actual,
                "first_break_record": first_break,
            },
        )

        for outcome in self._run_checks(
            payments,
            payment_breakdowns,
            settlement,
            bank_credit,
            expected_settlement,
        ):
            CheckResult.objects.update_or_create(
                reconciliation_case=reconciliation_case,
                check_name=outcome.name,
                defaults={
                    "result": outcome.result,
                    "evidence": outcome.evidence,
                    "details": outcome.details,
                },
            )

        EvidenceMatcher().build_connections(reconciliation_case, ordered_records)
        return reconciliation_case

    def _payment_breakdown(self, payment, ordered_records, single_payment) -> "PaymentBreakdown":
        order = self._order_for_payment(ordered_records, payment, single_payment)
        fee = self._linked_record(ordered_records, FinancialRecordType.FEE, payment, single_payment)
        tax = (
            self._linked_record(ordered_records, FinancialRecordType.TAX, fee, single_payment)
            if fee
            else None
        )
        expected_fee = self._apply_basis_points(payment.amount_minor, self.processing_fee_basis_points)
        expected_tax = self._apply_basis_points(expected_fee, self.tax_on_fee_basis_points)
        return PaymentBreakdown(
            order=order,
            payment=payment,
            fee=fee,
            tax=tax,
            captured_amount=payment.amount_minor,
            expected_fee=expected_fee,
            expected_tax=expected_tax,
        )

    def _order_for_payment(self, ordered_records, payment, single_payment):
        orders = [
            record for record in ordered_records if record.record_type == FinancialRecordType.ORDER
        ]
        if single_payment and len(orders) <= 1:
            return orders[0] if orders else None
        payment_reference = payment.reference or payment.raw_payload.get("linked_reference")
        return next(
            (order for order in orders if order.external_record_id == payment_reference),
            None,
        )

    def _linked_record(self, ordered_records, record_type, predecessor, single_payment):
        candidates = [
            record for record in ordered_records if record.record_type == record_type
        ]
        if single_payment and len(candidates) <= 1:
            return candidates[0] if candidates else None
        return next(
            (
                record
                for record in candidates
                if (record.reference or record.raw_payload.get("linked_reference"))
                == predecessor.external_record_id
            ),
            None,
        )

    def _classify(
        self,
        payments,
        payment_breakdowns,
        settlement,
        bank_credit,
        expected_settlement,
        actual_bank_amount,
    ):
        for breakdown in payment_breakdowns:
            if breakdown.fee and breakdown.fee.amount_minor != breakdown.expected_fee:
                return (
                    breakdown.fee,
                    "fee_mismatch",
                    ReconciliationStatus.NEEDS_REVIEW,
                    breakdown.expected_fee,
                    breakdown.fee.amount_minor,
                )
        for breakdown in payment_breakdowns:
            if breakdown.tax and breakdown.tax.amount_minor != breakdown.expected_tax:
                return (
                    breakdown.tax,
                    "tax_mismatch",
                    ReconciliationStatus.NEEDS_REVIEW,
                    breakdown.expected_tax,
                    breakdown.tax.amount_minor,
                )
        if not settlement:
            return (
                payments[-1],
                "settlement_missing",
                ReconciliationStatus.NEEDS_REVIEW,
                expected_settlement,
                0,
            )
        if settlement.amount_minor != expected_settlement:
            return (
                settlement,
                "settlement_mismatch",
                ReconciliationStatus.NEEDS_REVIEW,
                expected_settlement,
                settlement.amount_minor,
            )
        if not bank_credit:
            return settlement, "bank_credit_delayed", ReconciliationStatus.NEEDS_REVIEW, expected_settlement, 0
        if bank_credit.amount_minor != settlement.amount_minor:
            has_explanation = bool(bank_credit.raw_payload.get("adjustment_note"))
            status = (
                ReconciliationStatus.NEEDS_REVIEW
                if has_explanation
                else ReconciliationStatus.INSUFFICIENT_EVIDENCE
            )
            return (
                bank_credit,
                "settlement_short",
                status,
                settlement.amount_minor,
                actual_bank_amount,
            )
        return None, "clean_match", ReconciliationStatus.MATCHED, expected_settlement, actual_bank_amount

    def _run_checks(
        self,
        payments,
        payment_breakdowns,
        settlement,
        bank_credit,
        expected_settlement,
    ) -> list[RuleOutcome]:
        single_payment = len(payments) == 1
        checks = []
        for breakdown in payment_breakdowns:
            suffix = "" if single_payment else f" ({breakdown.payment.external_record_id})"
            checks.append(
                self._comparison(
                    f"Order amount matches capture{suffix}",
                    breakdown.order,
                    breakdown.payment,
                    breakdown.order.amount_minor if breakdown.order else None,
                    breakdown.payment.amount_minor,
                )
            )
            checks.append(
                self._comparison(
                    f"Processing fee calculation{suffix}",
                    breakdown.payment,
                    breakdown.fee,
                    breakdown.expected_fee,
                    breakdown.fee.amount_minor if breakdown.fee else None,
                )
            )
            checks.append(
                self._comparison(
                    f"Tax on fee calculation{suffix}",
                    breakdown.fee,
                    breakdown.tax,
                    breakdown.expected_tax,
                    breakdown.tax.amount_minor if breakdown.tax else None,
                )
            )
        checks.append(
            self._comparison(
                "Settlement amount calculation",
                payments[0],
                settlement,
                expected_settlement,
                settlement.amount_minor if settlement else None,
            )
        )
        checks.append(
            RuleOutcome(
                "Settlement acknowledged by bank",
                CheckResultStatus.PASSED if bank_credit else CheckResultStatus.WAITING,
                self._references(settlement, bank_credit),
                "Bank credit found." if bank_credit else "No bank credit has been ingested yet.",
            )
        )
        checks.append(
            self._comparison(
                "Bank credit equals settlement",
                settlement,
                bank_credit,
                settlement.amount_minor if settlement else None,
                bank_credit.amount_minor if bank_credit else None,
            )
        )
        checks.append(
            RuleOutcome(
                "Reconciliation note present",
                (
                    CheckResultStatus.PASSED
                    if bank_credit and bank_credit.raw_payload.get("adjustment_note")
                    else CheckResultStatus.WAITING
                ),
                self._references(bank_credit),
                "An adjustment note explains the difference."
                if bank_credit and bank_credit.raw_payload.get("adjustment_note")
                else "No adjustment record explains the difference.",
            )
        )
        return checks

    def _comparison(self, name, first_record, second_record, expected, actual) -> RuleOutcome:
        if expected is None or actual is None:
            result = CheckResultStatus.WAITING
            details = "A required record has not been ingested."
        elif expected == actual:
            result = CheckResultStatus.PASSED
            details = "Expected and actual amounts match."
        else:
            result = CheckResultStatus.FAILED
            details = f"Expected {expected} minor units; received {actual}."
        return RuleOutcome(name, result, self._references(first_record, second_record), details)

    @staticmethod
    def _first(records, record_type):
        return next((record for record in records if record.record_type == record_type), None)

    @staticmethod
    def _sum(records, record_type):
        return sum(record.amount_minor for record in records if record.record_type == record_type)

    @staticmethod
    def _apply_basis_points(amount_minor: int, basis_points: int) -> int:
        return (amount_minor * basis_points + 5_000) // 10_000

    @staticmethod
    def _references(*records) -> list[str]:
        return [record.external_record_id for record in records if record]
