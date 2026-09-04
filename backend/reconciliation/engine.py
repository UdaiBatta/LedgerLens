from dataclasses import dataclass

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
        order = self._first(ordered_records, FinancialRecordType.ORDER)
        payment = self._first(ordered_records, FinancialRecordType.PAYMENT)
        fee = self._first(ordered_records, FinancialRecordType.FEE)
        tax = self._first(ordered_records, FinancialRecordType.TAX)
        settlement = self._first(ordered_records, FinancialRecordType.SETTLEMENT)
        bank_credit = self._first(ordered_records, FinancialRecordType.BANK_CREDIT)
        refunds = self._sum(ordered_records, FinancialRecordType.REFUND)

        captured_amount = payment.amount_minor if payment else 0
        expected_fee = self._apply_basis_points(captured_amount, self.processing_fee_basis_points)
        expected_tax = self._apply_basis_points(expected_fee, self.tax_on_fee_basis_points)
        expected_settlement = captured_amount - refunds - expected_fee - expected_tax
        actual_amount = bank_credit.amount_minor if bank_credit else 0

        first_break, exception_type, status = self._classify(
            payment,
            fee,
            tax,
            settlement,
            bank_credit,
            expected_fee,
            expected_tax,
            expected_settlement,
        )

        reconciliation_case, _ = ReconciliationCase.objects.update_or_create(
            organization=organization,
            case_reference=case_reference,
            defaults={
                "entity_id": entity_id,
                "exception_type": exception_type,
                "status": status,
                "currency": payment.currency if payment else "INR",
                "expected_amount_minor": expected_settlement,
                "actual_amount_minor": actual_amount,
                "first_break_record": first_break,
            },
        )

        for outcome in self._run_checks(
            order,
            payment,
            fee,
            tax,
            settlement,
            bank_credit,
            expected_fee,
            expected_tax,
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

    def _classify(
        self,
        payment,
        fee,
        tax,
        settlement,
        bank_credit,
        expected_fee,
        expected_tax,
        expected_settlement,
    ):
        if fee and fee.amount_minor != expected_fee:
            return fee, "fee_mismatch", ReconciliationStatus.NEEDS_REVIEW
        if tax and tax.amount_minor != expected_tax:
            return tax, "tax_mismatch", ReconciliationStatus.NEEDS_REVIEW
        if not settlement:
            return payment, "settlement_missing", ReconciliationStatus.NEEDS_REVIEW
        if settlement.amount_minor != expected_settlement:
            return settlement, "settlement_mismatch", ReconciliationStatus.NEEDS_REVIEW
        if not bank_credit:
            return settlement, "bank_credit_delayed", ReconciliationStatus.NEEDS_REVIEW
        if bank_credit.amount_minor != settlement.amount_minor:
            has_explanation = bool(bank_credit.raw_payload.get("adjustment_note"))
            status = (
                ReconciliationStatus.NEEDS_REVIEW
                if has_explanation
                else ReconciliationStatus.INSUFFICIENT_EVIDENCE
            )
            return bank_credit, "settlement_short", status
        return None, "clean_match", ReconciliationStatus.MATCHED

    def _run_checks(
        self,
        order,
        payment,
        fee,
        tax,
        settlement,
        bank_credit,
        expected_fee,
        expected_tax,
        expected_settlement,
    ) -> list[RuleOutcome]:
        return [
            self._comparison(
                "Order amount matches capture",
                order,
                payment,
                order.amount_minor if order else None,
                payment.amount_minor if payment else None,
            ),
            self._comparison(
                "Processing fee calculation",
                payment,
                fee,
                expected_fee,
                fee.amount_minor if fee else None,
            ),
            self._comparison(
                "Tax on fee calculation",
                fee,
                tax,
                expected_tax,
                tax.amount_minor if tax else None,
            ),
            self._comparison(
                "Settlement amount calculation",
                payment,
                settlement,
                expected_settlement,
                settlement.amount_minor if settlement else None,
            ),
            RuleOutcome(
                "Settlement acknowledged by bank",
                CheckResultStatus.PASSED if bank_credit else CheckResultStatus.WAITING,
                self._references(settlement, bank_credit),
                "Bank credit found." if bank_credit else "No bank credit has been ingested yet.",
            ),
            self._comparison(
                "Bank credit equals settlement",
                settlement,
                bank_credit,
                settlement.amount_minor if settlement else None,
                bank_credit.amount_minor if bank_credit else None,
            ),
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
            ),
        ]

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
