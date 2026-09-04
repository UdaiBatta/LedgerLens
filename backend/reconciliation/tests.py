import json
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .agent import InvestigationAgent
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

    def test_raw_source_payload_cannot_be_changed_after_ingestion(self) -> None:
        record = self.create_financial_record(
            self.gateway,
            "PAY-IMMUTABLE",
            FinancialRecordType.PAYMENT,
            100_000,
        )
        record.raw_payload = {"changed": True}

        with self.assertRaises(ValidationError):
            record.save()


class DemoReconciliationFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        call_command("seed_demo_cases", verbosity=0)

    def test_seed_is_idempotent_and_builds_all_scenarios(self) -> None:
        original_record_count = FinancialRecord.objects.count()
        call_command("seed_demo_cases", verbosity=0)

        self.assertEqual(ReconciliationCase.objects.count(), 6)
        self.assertGreaterEqual(original_record_count, 200)
        self.assertEqual(FinancialRecord.objects.count(), original_record_count)

    def test_settlement_short_case_has_exact_first_break(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000145"
        )

        self.assertEqual(reconciliation_case.difference_minor, -340)
        self.assertEqual(reconciliation_case.status, ReconciliationStatus.INSUFFICIENT_EVIDENCE)
        self.assertEqual(
            reconciliation_case.first_break_record.record_type,
            FinancialRecordType.BANK_CREDIT,
        )
        self.assertEqual(reconciliation_case.check_results.count(), 7)

    def test_every_seeded_scenario_has_the_expected_outcome(self) -> None:
        expected_outcomes = {
            "EXC-2025-05-000150": ("clean_match", ReconciliationStatus.MATCHED),
            "EXC-2025-05-000145": (
                "settlement_short",
                ReconciliationStatus.INSUFFICIENT_EVIDENCE,
            ),
            "EXC-2025-05-000142": ("fee_mismatch", ReconciliationStatus.NEEDS_REVIEW),
            "EXC-2025-05-000138": (
                "bank_credit_delayed",
                ReconciliationStatus.NEEDS_REVIEW,
            ),
            "EXC-2025-05-000137": (
                "settlement_mismatch",
                ReconciliationStatus.NEEDS_REVIEW,
            ),
            "EXC-2025-05-000131": ("clean_match", ReconciliationStatus.MATCHED),
        }

        for case_reference, expected in expected_outcomes.items():
            reconciliation_case = ReconciliationCase.objects.get(
                case_reference=case_reference
            )
            self.assertEqual(
                (reconciliation_case.exception_type, reconciliation_case.status),
                expected,
            )
            self.assertEqual(reconciliation_case.check_results.count(), 7)

    def test_matcher_records_a_fuzzy_link_with_rationale(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000145"
        )
        fuzzy_link = reconciliation_case.evidence_connections.get(
            destination_record__record_type=FinancialRecordType.BANK_CREDIT
        )

        self.assertEqual(fuzzy_link.match_method, EvidenceMatchMethod.AMOUNT_AND_TIME)
        self.assertEqual(fuzzy_link.confidence, Decimal("0.7500"))
        self.assertIn("amount_difference_minor", fuzzy_link.rationale)

    def test_case_api_returns_distinct_real_cases_and_agent_history(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000145"
        )
        list_response = self.client.get("/api/cases/")
        detail_response = self.client.get(f"/api/cases/{reconciliation_case.public_id}/")
        ask_response = self.client.post(
            f"/api/cases/{reconciliation_case.public_id}/ask/",
            {"question": "Why is the settlement short?"},
            content_type="application/json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 6)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["difference_minor"], -340)
        self.assertEqual(ask_response.status_code, 201)
        self.assertFalse(ask_response.json()["sufficient_evidence"])
        self.assertEqual(reconciliation_case.agent_runs.count(), 1)

    def test_operational_endpoints_return_graph_metrics_and_assignment(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000145"
        )
        graph_response = self.client.get(
            f"/api/cases/{reconciliation_case.public_id}/evidence-graph/"
        )
        metrics_response = self.client.get("/api/metrics/overview/")
        assignment_response = self.client.post(
            f"/api/cases/{reconciliation_case.public_id}/assign/",
            {"owner": "Neha Sharma"},
            content_type="application/json",
        )

        self.assertEqual(graph_response.status_code, 200)
        self.assertEqual(len(graph_response.json()["nodes"]), 7)
        self.assertEqual(len(graph_response.json()["edges"]), 6)
        self.assertEqual(metrics_response.status_code, 200)
        self.assertEqual(metrics_response.json()["case_count"], 6)
        self.assertEqual(assignment_response.status_code, 200)
        self.assertEqual(assignment_response.json()["owner"], "Neha Sharma")

    def test_money_engine_does_not_import_the_agent_layer(self) -> None:
        engine_source = Path(__file__).with_name("engine.py").read_text(encoding="utf-8")

        self.assertNotIn("from .agent", engine_source)
        self.assertNotIn("import agent", engine_source)


class SystemHealthViewTests(TestCase):
    def test_health_endpoint_reports_service_name(self) -> None:
        response = self.client.get(reverse("system-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "ledgerlens-backend"},
        )


class InvestigationAgentValidationTests(TestCase):
    def test_rejects_out_of_range_confidence(self) -> None:
        response = json.dumps(
            {
                "conclusion": "A conclusion.",
                "confidence": 1.2,
                "evidence_cited": [],
                "sufficient_evidence": False,
            }
        )

        with self.assertRaises(ValueError):
            InvestigationAgent._parse_result(response)

    def test_rejects_citations_not_returned_by_tools(self) -> None:
        result = {
            "conclusion": "A conclusion.",
            "confidence": 0.8,
            "evidence_cited": ["TXN-INVENTED"],
            "sufficient_evidence": False,
        }

        with self.assertRaises(ValueError):
            InvestigationAgent._validate_citations(
                result,
                [{"result": {"found": True, "record_id": "TXN-REAL"}}],
            )
