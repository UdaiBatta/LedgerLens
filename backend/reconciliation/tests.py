from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    EvidenceConnection,
    EvidenceMatchMethod,
    FinancialDataSource,
    FinancialDirection,
    FinancialRecord,
    FinancialRecordType,
    FinancialSourceType,
    Organization,
    ReconciliationCase,
    ReconciliationStatus,
)


class ReconciliationEvidenceModelTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(
            name="Example Payments",
            slug="example-payments",
        )
        self.gateway = FinancialDataSource.objects.create(
            organization=self.organization,
            name="Payment Gateway",
            source_type=FinancialSourceType.PAYMENT_GATEWAY,
        )
        self.bank = FinancialDataSource.objects.create(
            organization=self.organization,
            name="Settlement Bank",
            source_type=FinancialSourceType.BANK_ACCOUNT,
        )

    def create_financial_record(
        self,
        source: FinancialDataSource,
        external_record_id: str,
        record_type: str,
        amount_minor: int,
    ) -> FinancialRecord:
        return FinancialRecord.objects.create(
            source=source,
            external_record_id=external_record_id,
            record_type=record_type,
            direction=FinancialDirection.CREDIT,
            amount_minor=amount_minor,
            currency="INR",
            occurred_at=timezone.now(),
            content_hash=external_record_id.lower().ljust(64, "0"),
            raw_payload={"external_record_id": external_record_id},
        )

    def test_case_exposes_first_break_and_exact_difference(self) -> None:
        settlement = self.create_financial_record(
            self.gateway,
            "SET-55667788",
            FinancialRecordType.SETTLEMENT,
            985_840,
        )
        bank_credit = self.create_financial_record(
            self.bank,
            "TXN-11223344",
            FinancialRecordType.BANK_CREDIT,
            985_500,
        )
        reconciliation_case = ReconciliationCase.objects.create(
            organization=self.organization,
            case_reference="INV-2025-05-19-0001",
            status=ReconciliationStatus.NEEDS_REVIEW,
            currency="INR",
            expected_amount_minor=985_840,
            actual_amount_minor=985_500,
            first_break_record=bank_credit,
        )
        connection = EvidenceConnection.objects.create(
            reconciliation_case=reconciliation_case,
            source_record=settlement,
            destination_record=bank_credit,
            sequence_number=1,
            match_method=EvidenceMatchMethod.SOURCE_REFERENCE,
            confidence=Decimal("1.0000"),
            matching_reason="The settlement reference is present in the bank narration.",
            is_verified=True,
        )

        self.assertEqual(reconciliation_case.difference_minor, -340)
        self.assertEqual(reconciliation_case.first_break_record, bank_credit)
        self.assertTrue(connection.is_verified)


class SystemHealthViewTests(TestCase):
    def test_health_endpoint_reports_service_name(self) -> None:
        response = self.client.get(reverse("system-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "ledgerlens-backend"},
        )
