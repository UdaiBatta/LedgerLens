import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .agent import InvestigationAgent
from .bank_statement_adapter import parse_bank_statement_csv
from .engine import ReconciliationEngine
from .matcher import EvidenceMatcher
from .models import (
    EvidenceConnection,
    EvidenceMatchMethod,
    FinancialDataSource,
    FinancialDirection,
    FinancialRecord,
    FinancialRecordType,
    FinancialSourceType,
    IngestionBatchStatus,
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

    def test_matcher_does_not_link_unrelated_records_by_sequence_alone(self) -> None:
        settlement = self.create_financial_record(
            self.gateway,
            "SET-UNRELATED",
            FinancialRecordType.SETTLEMENT,
            100_000,
        )
        bank_credit = self.create_financial_record(
            self.bank,
            "TXN-UNRELATED",
            FinancialRecordType.BANK_CREDIT,
            10_000,
        )
        reconciliation_case = ReconciliationCase.objects.create(
            organization=self.organization,
            case_reference="CASE-UNRELATED",
            currency="INR",
            expected_amount_minor=100_000,
            actual_amount_minor=10_000,
        )

        connections = EvidenceMatcher().build_connections(
            reconciliation_case,
            [settlement, bank_credit],
        )

        self.assertEqual(connections, [])

    def test_matcher_prefers_an_explicit_record_reference(self) -> None:
        settlement = self.create_financial_record(
            self.gateway,
            "SET-EXACT",
            FinancialRecordType.SETTLEMENT,
            100_000,
        )
        bank_credit = self.create_financial_record(
            self.bank,
            "TXN-EXACT",
            FinancialRecordType.BANK_CREDIT,
            100_000,
        )
        bank_credit.reference = settlement.external_record_id
        bank_credit.save(update_fields=["reference"])
        reconciliation_case = ReconciliationCase.objects.create(
            organization=self.organization,
            case_reference="CASE-EXACT",
            currency="INR",
            expected_amount_minor=100_000,
            actual_amount_minor=100_000,
        )

        connection = EvidenceMatcher().build_connections(
            reconciliation_case,
            [settlement, bank_credit],
        )[0]

        self.assertEqual(connection.source_record, settlement)
        self.assertEqual(connection.match_method, EvidenceMatchMethod.EXACT_REFERENCE)
        self.assertEqual(connection.confidence, Decimal("1.0000"))


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

    def test_fee_mismatch_case_reports_the_fee_variance_not_the_settlement_variance(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000142"
        )

        self.assertEqual(reconciliation_case.exception_type, "fee_mismatch")
        self.assertEqual(reconciliation_case.first_break_record.record_type, FinancialRecordType.FEE)
        self.assertEqual(reconciliation_case.expected_amount_minor, 30_000)
        self.assertEqual(reconciliation_case.actual_amount_minor, 35_000)
        self.assertEqual(reconciliation_case.difference_minor, 5_000)

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

        audit_response = self.client.get("/api/audit-log/")
        self.assertEqual(audit_response.status_code, 200)
        self.assertGreater(len(audit_response.json()), 0)

    def test_money_engine_does_not_import_the_agent_layer(self) -> None:
        engine_source = Path(__file__).with_name("engine.py").read_text(encoding="utf-8")

        self.assertNotIn("from .agent", engine_source)
        self.assertNotIn("import agent", engine_source)

    def test_engine_requires_at_least_one_payment(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000150"
        )
        records = [
            record
            for record in FinancialRecord.objects.filter(entity_id=reconciliation_case.entity_id)
            if record.record_type != FinancialRecordType.PAYMENT
        ]

        with self.assertRaises(ValidationError):
            ReconciliationEngine().reconcile(
                reconciliation_case.organization,
                "CASE-NO-PAYMENT",
                reconciliation_case.entity_id,
                records,
            )

    def test_engine_batches_two_payments_into_one_settlement(self) -> None:
        reconciliation_case = ReconciliationCase.objects.get(
            case_reference="EXC-2025-05-000150"
        )
        source = FinancialRecord.objects.filter(
            entity_id=reconciliation_case.entity_id, record_type=FinancialRecordType.PAYMENT
        ).first().source
        started_at = timezone.now()

        def make(external_id, record_type, amount_minor, minute, reference="", extra_payload=None):
            return FinancialRecord.objects.create(
                source=source,
                external_record_id=external_id,
                record_type=record_type,
                entity_id="Batched Settlement Entity",
                direction=FinancialDirection.CREDIT,
                amount_minor=amount_minor,
                currency="INR",
                occurred_at=started_at + timedelta(minutes=minute),
                reference=reference,
                content_hash=external_id.lower().ljust(64, "0"),
                raw_payload={"linked_reference": reference, **(extra_payload or {})},
            )

        payment_1 = make("PAY-BATCH-1", FinancialRecordType.PAYMENT, 100_000, 1)
        fee_1 = make("FEE-BATCH-1", FinancialRecordType.FEE, 1_200, 2, reference=payment_1.external_record_id)
        tax_1 = make("TAX-BATCH-1", FinancialRecordType.TAX, 216, 3, reference=fee_1.external_record_id)

        payment_2 = make("PAY-BATCH-2", FinancialRecordType.PAYMENT, 200_000, 4)
        fee_2 = make("FEE-BATCH-2", FinancialRecordType.FEE, 2_400, 5, reference=payment_2.external_record_id)
        tax_2 = make("TAX-BATCH-2", FinancialRecordType.TAX, 432, 6, reference=fee_2.external_record_id)

        combined_settlement_amount = (100_000 - 1_200 - 216) + (200_000 - 2_400 - 432)
        combined_settlement = make(
            "SET-BATCH-COMBINED",
            FinancialRecordType.SETTLEMENT,
            combined_settlement_amount,
            7,
            extra_payload={
                "contributing_references": [tax_1.external_record_id, tax_2.external_record_id],
            },
        )

        records = [payment_1, fee_1, tax_1, payment_2, fee_2, tax_2, combined_settlement]
        batched_case = ReconciliationEngine().reconcile(
            reconciliation_case.organization,
            "CASE-BATCHED",
            "Batched Settlement Entity",
            records,
        )

        self.assertEqual(batched_case.exception_type, "bank_credit_delayed")
        self.assertEqual(batched_case.expected_amount_minor, combined_settlement_amount)
        self.assertEqual(
            batched_case.check_results.filter(
                check_name__startswith="Processing fee calculation ("
            ).count(),
            2,
        )

        connections = {
            (connection.source_record.external_record_id, connection.destination_record.external_record_id)
            for connection in batched_case.evidence_connections.all()
        }
        self.assertEqual(
            connections,
            {
                ("PAY-BATCH-1", "FEE-BATCH-1"),
                ("FEE-BATCH-1", "TAX-BATCH-1"),
                ("PAY-BATCH-2", "FEE-BATCH-2"),
                ("FEE-BATCH-2", "TAX-BATCH-2"),
                ("TAX-BATCH-1", "SET-BATCH-COMBINED"),
                ("TAX-BATCH-2", "SET-BATCH-COMBINED"),
            },
        )


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


class FinancialRecordIngestionApiTests(TestCase):
    def setUp(self) -> None:
        self.payload = {
            "organization_slug": "api-demo",
            "organization_name": "API Demo",
            "source_name": "Unified Test Feed",
            "source_type": FinancialSourceType.PAYMENT_GATEWAY,
            "batch_reference": "BATCH-001",
            "records": [
                self.record("ORD-API-1", FinancialRecordType.ORDER, 100_000, "10:00:00"),
                self.record(
                    "PAY-API-1",
                    FinancialRecordType.PAYMENT,
                    100_000,
                    "10:01:00",
                    "ORD-API-1",
                ),
                self.record(
                    "FEE-API-1",
                    FinancialRecordType.FEE,
                    1_200,
                    "10:02:00",
                    "PAY-API-1",
                ),
                self.record(
                    "TAX-API-1",
                    FinancialRecordType.TAX,
                    216,
                    "10:03:00",
                    "FEE-API-1",
                ),
                self.record(
                    "SET-API-1",
                    FinancialRecordType.SETTLEMENT,
                    98_584,
                    "10:04:00",
                    "TAX-API-1",
                ),
                self.record(
                    "TXN-API-1",
                    FinancialRecordType.BANK_CREDIT,
                    98_584,
                    "10:05:00",
                    "SET-API-1",
                ),
            ],
            "reconcile": {
                "case_reference": "CASE-API-1",
                "entity_id": "TRACE-API-1",
            },
        }

    @staticmethod
    def record(external_id, record_type, amount_minor, time, reference=""):
        return {
            "external_record_id": external_id,
            "record_type": record_type,
            "entity_id": "TRACE-API-1",
            "amount_minor": amount_minor,
            "currency": "INR",
            "occurred_at": f"2026-09-04T{time}+00:00",
            "reference": reference,
            "raw_payload": {
                "external_record_id": external_id,
                "reference": reference,
                "amount_minor": amount_minor,
            },
        }

    def test_ingestion_can_create_records_and_run_reconciliation(self) -> None:
        response = self.client.post(
            "/api/ingestion/batches/",
            self.payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["batch"]["status"], IngestionBatchStatus.PROCESSED)
        self.assertEqual(response.json()["batch"]["imported_count"], 6)
        self.assertEqual(response.json()["reconciliation_case"]["status"], "matched")
        self.assertEqual(FinancialRecord.objects.count(), 6)

    def test_replaying_the_same_batch_is_a_no_op(self) -> None:
        first_response = self.client.post(
            "/api/ingestion/batches/",
            self.payload,
            content_type="application/json",
        )
        second_response = self.client.post(
            "/api/ingestion/batches/",
            self.payload,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.json()["replayed"])
        self.assertEqual(FinancialRecord.objects.count(), 6)

    def test_reused_batch_reference_with_changed_data_is_rejected(self) -> None:
        self.client.post(
            "/api/ingestion/batches/",
            self.payload,
            content_type="application/json",
        )
        changed_payload = {**self.payload, "records": [dict(self.payload["records"][0])]}
        changed_payload["records"][0]["amount_minor"] = 999

        response = self.client.post(
            "/api/ingestion/batches/",
            changed_payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(FinancialRecord.objects.count(), 6)

    def test_invalid_rows_are_preserved_as_batch_errors(self) -> None:
        invalid_payload = {
            **self.payload,
            "batch_reference": "BATCH-INVALID",
            "records": [
                {
                    **self.payload["records"][0],
                    "external_record_id": "ORD-BAD",
                    "amount_minor": 10.5,
                }
            ],
            "reconcile": None,
        }

        response = self.client.post(
            "/api/ingestion/batches/",
            invalid_payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["batch"]["status"], IngestionBatchStatus.REJECTED)
        self.assertEqual(response.json()["batch"]["rejected_count"], 1)
        self.assertIn("amount_minor", response.json()["batch"]["errors"][0]["reason"])

    def test_new_batch_cannot_replace_existing_immutable_evidence(self) -> None:
        initial_payload = {**self.payload, "reconcile": None}
        self.client.post(
            "/api/ingestion/batches/",
            initial_payload,
            content_type="application/json",
        )
        conflicting_record = {
            **self.payload["records"][0],
            "amount_minor": 999,
        }
        conflicting_payload = {
            **initial_payload,
            "batch_reference": "BATCH-002",
            "records": [conflicting_record],
        }

        response = self.client.post(
            "/api/ingestion/batches/",
            conflicting_payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["batch"]["status"], IngestionBatchStatus.REJECTED)
        original = FinancialRecord.objects.get(external_record_id="ORD-API-1")
        self.assertEqual(original.raw_payload["amount_minor"], 100_000)
        self.assertEqual(original.amount_minor, 100_000)

    def test_ingestion_remains_auditable_when_reconciliation_cannot_run(self) -> None:
        order_only_payload = {
            **self.payload,
            "batch_reference": "BATCH-ORDER-ONLY",
            "records": [self.payload["records"][0]],
        }

        response = self.client.post(
            "/api/ingestion/batches/",
            order_only_payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["batch"]["status"], IngestionBatchStatus.PROCESSED)
        self.assertIn("reconciliation_error", response.json())


class BankStatementAdapterTests(TestCase):
    def test_parses_a_well_formed_bank_statement_row(self) -> None:
        records = parse_bank_statement_csv(
            "transaction_reference,amount_minor,value_date,narration,settlement_reference,entity_id\n"
            "TXN-CSV-1,50000,2025-05-19T14:00:00Z,NEFT credit,SET-CSV-1,Nova Commerce\n"
        )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["external_record_id"], "TXN-CSV-1")
        self.assertEqual(record["record_type"], FinancialRecordType.BANK_CREDIT)
        self.assertEqual(record["amount_minor"], 50_000)
        self.assertEqual(record["reference"], "SET-CSV-1")
        self.assertEqual(record["raw_payload"]["linked_reference"], "SET-CSV-1")

    def test_rejects_a_csv_missing_required_columns(self) -> None:
        with self.assertRaises(ValueError):
            parse_bank_statement_csv("amount_minor,value_date\n50000,2025-05-19T14:00:00Z\n")

    def test_rejects_a_non_numeric_amount(self) -> None:
        with self.assertRaises(ValueError):
            parse_bank_statement_csv(
                "transaction_reference,amount_minor,value_date\n"
                "TXN-BAD,not-a-number,2025-05-19T14:00:00Z\n"
            )


class ImportBankStatementCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        call_command("seed_demo_cases", verbosity=0)

    def test_importing_the_missing_bank_credit_resolves_the_delayed_case(self) -> None:
        csv_path = Path(self.id().replace(".", "_")).with_suffix(".csv")
        csv_path.write_text(
            "transaction_reference,amount_minor,value_date,narration,settlement_reference,entity_id\n"
            "TXN-000138,837964,2025-05-18T14:00:00Z,NEFT credit,SET-000138,Zenith Supplies\n",
            encoding="utf-8",
        )
        try:
            call_command(
                "import_bank_statement",
                str(csv_path),
                organization_slug="ledgerlens-demo",
                source_name="HDFC Current Account",
                batch_reference="hdfc-test-batch",
                reconcile_entity="Zenith Supplies",
            )
        finally:
            csv_path.unlink(missing_ok=True)

        record = FinancialRecord.objects.get(external_record_id="TXN-000138")
        self.assertEqual(record.record_type, FinancialRecordType.BANK_CREDIT)
        self.assertEqual(record.amount_minor, 837_964)

        reconciliation_case = ReconciliationCase.objects.get(case_reference="hdfc-test-batch")
        self.assertEqual(reconciliation_case.exception_type, "clean_match")
        self.assertEqual(reconciliation_case.status, ReconciliationStatus.MATCHED)

    def test_replaying_the_same_batch_reference_does_not_duplicate_records(self) -> None:
        csv_path = Path(self.id().replace(".", "_")).with_suffix(".csv")
        csv_path.write_text(
            "transaction_reference,amount_minor,value_date,settlement_reference,entity_id\n"
            "TXN-REPLAY-1,12345,2025-05-19T14:00:00Z,SET-REPLAY-1,Nova Commerce\n",
            encoding="utf-8",
        )
        try:
            for _ in range(2):
                call_command(
                    "import_bank_statement",
                    str(csv_path),
                    organization_slug="ledgerlens-demo",
                    source_name="HDFC Current Account",
                    batch_reference="hdfc-replay-batch",
                )
        finally:
            csv_path.unlink(missing_ok=True)

        self.assertEqual(
            FinancialRecord.objects.filter(external_record_id="TXN-REPLAY-1").count(), 1
        )
