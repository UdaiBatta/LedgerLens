from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction, DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone

from .engine import ReconciliationEngine
from .ingestion import FinancialRecordIngestionService
from .matcher import EvidenceMatcher
from .agent import InvestigationAgent
from .models import (FinancialDataSource, FinancialRecord, Organization, OrganizationMembership,
                     ReconciliationRuleVersion, ReconciliationRun, AuditEvent, IngestionDelivery)


class FinancialControlTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Control Test", slug="control-test")
        self.source = FinancialDataSource.objects.create(organization=self.organization, name="Gateway", source_type="payment_gateway")
        self.time = timezone.now() - timedelta(days=3)
        self.rule = ReconciliationRuleVersion.objects.create(source=self.source, version="contract-v1", currency="INR",
            effective_from=self.time - timedelta(days=10), effective_until=self.time + timedelta(days=1),
            fee_basis_points=120, tax_basis_points=1800)

    def record(self, ref, kind, amount, reference="", **extra):
        return FinancialRecord.objects.create(source=self.source, external_record_id=ref, record_type=kind,
            entity_id="scope-1", direction="debit" if kind in {"fee", "tax", "refund"} else "credit",
            amount_minor=amount, currency=extra.pop("currency", "INR"), occurred_at=self.time,
            status=extra.pop("status", "processed"), reference=reference,
            raw_payload=extra, content_hash="0" * 64)

    def chain(self, *, refund_amounts=(), fee=1200, tax=216, settlement=None, bank=None, ledger=None, missing=()):
        net = 100000 - 1200 - 216 - sum(refund_amounts)
        result = [self.record("O", "order", 100000), self.record("P", "payment", 100000, "O"),
                  self.record("F", "fee", fee, "P"), self.record("T", "tax", tax, "F")]
        result += [self.record(f"R{i}", "refund", amount, "P") for i, amount in enumerate(refund_amounts)]
        result += [self.record("S", "settlement", net if settlement is None else settlement, "T"),
                   self.record("B", "bank_credit", net if bank is None else bank, "S"),
                   self.record("L", "ledger_entry", net if ledger is None else ledger, "B")]
        return [r for r in result if r.record_type not in missing]

    def reconcile(self, records, **kwargs):
        return ReconciliationEngine().reconcile(self.organization, "CASE-1", "scope-1", records, **kwargs)

    def test_clean_and_immutable_run(self):
        case = self.reconcile(self.chain())
        self.assertEqual((case.status, case.difference_minor), ("matched", 0))
        run = case.reconciliation_runs.first()
        self.assertEqual(run.rules[0]["id"], self.rule.pk)
        self.assertEqual(len(run.inputs), 7)
        self.assertTrue(all(c["result"] == "passed" for c in run.checks))
        with self.assertRaises(ValidationError):
            ReconciliationRun.objects.filter(pk=run.pk).update(result={})

    def test_partial_refund(self):
        case = self.reconcile(self.chain(refund_amounts=(25000,)))
        self.assertEqual((case.status, case.actual_amount_minor), ("matched", 73584))

    def test_multiple_refunds(self):
        case = self.reconcile(self.chain(refund_amounts=(20000, 30000)))
        self.assertEqual((case.status, case.actual_amount_minor), ("matched", 48584))

    def test_fee_is_first_break(self):
        case = self.reconcile(self.chain(fee=1500))
        self.assertEqual((case.exception_type, case.difference_minor), ("fee_mismatch", 300))

    def test_tax_is_first_break(self):
        case = self.reconcile(self.chain(tax=250))
        self.assertEqual((case.exception_type, case.difference_minor), ("tax_mismatch", 34))

    def test_bank_shortfall_is_proved_even_if_cause_unknown(self):
        case = self.reconcile(self.chain(bank=98244, ledger=98244))
        self.assertEqual((case.exception_type, case.difference_minor), ("settlement_short", -340))

    def test_missing_gl_never_matches(self):
        case = self.reconcile(self.chain(missing=("ledger_entry",)))
        self.assertEqual(case.exception_type, "ledger_posting_missing")
        self.assertIsNone(case.reconciliation_runs.first().result["difference_minor"])

    def test_wrong_gl_is_first_break(self):
        case = self.reconcile(self.chain(ledger=98000))
        self.assertEqual((case.exception_type, case.difference_minor), ("ledger_mismatch", -584))

    def test_missing_fee_never_matches(self):
        case = self.reconcile(self.chain(missing=("fee",)))
        self.assertEqual(case.status, "insufficient_evidence")

    def test_missing_settlement_and_bank_are_overdue(self):
        case = self.reconcile(self.chain(missing=("settlement", "bank_credit", "ledger_entry")))
        self.assertEqual(case.exception_type, "settlement_overdue")

    def test_bank_not_yet_due_then_overdue_without_rewriting_history(self):
        self.time = timezone.now()
        ReconciliationRuleVersion.objects.create(source=self.source, version="contract-v2", currency="INR",
            effective_from=self.time - timedelta(hours=1), fee_basis_points=120, tax_basis_points=1800)
        records = self.chain(missing=("bank_credit", "ledger_entry"))
        case = self.reconcile(records)
        first = case.reconciliation_runs.first()
        self.assertEqual(case.exception_type, "bank_credit_not_yet_due")
        case = self.reconcile(records, as_of=timezone.now() + timedelta(days=4))
        first.refresh_from_db()
        self.assertEqual(first.result["exception_type"], "bank_credit_not_yet_due")
        self.assertEqual(case.exception_type, "bank_credit_overdue")
        self.assertEqual(case.reconciliation_runs.count(), 2)

    def test_multiple_bank_credits_sum_and_check_each_ledger_receipt(self):
        records = self.chain(missing=("bank_credit", "ledger_entry"))
        records += [self.record("B1", "bank_credit", 50000, "S"), self.record("B2", "bank_credit", 48584, "S"),
                    self.record("L1", "ledger_entry", 50000, "B1"), self.record("L2", "ledger_entry", 48584, "B2")]
        self.assertEqual(self.reconcile(records).status, "matched")

    def test_multiple_settlements_block_without_allocations(self):
        records = self.chain() + [self.record("S2", "settlement", 1, "T")]
        self.assertEqual(self.reconcile(records).exception_type, "unsupported_allocation")

    def test_out_of_order_input_same_checks(self):
        records = self.chain()
        original = self.reconcile(records).reconciliation_runs.first()
        rerun = self.reconcile(list(reversed(records))).reconciliation_runs.first()
        self.assertEqual(original.checks, rerun.checks)
        self.assertEqual(original.decisions, rerun.decisions)

    def test_new_evidence_appends_run(self):
        records = self.chain()
        case = self.reconcile([r for r in records if r.record_type != "ledger_entry"])
        first = case.reconciliation_runs.first()
        self.assertEqual(self.reconcile(records).status, "matched")
        first.refresh_from_db()
        self.assertEqual(first.result["exception_type"], "ledger_posting_missing")

    def test_rule_history_stable_when_future_pricing_changes(self):
        records = self.chain()
        original = self.reconcile(records).reconciliation_runs.first()
        ReconciliationRuleVersion.objects.create(source=self.source, version="next", currency="INR",
            effective_from=self.time + timedelta(days=1), fee_basis_points=900, tax_basis_points=2000)
        rerun = self.reconcile(records).reconciliation_runs.first()
        self.assertEqual(original.rules, rerun.rules)
        self.assertEqual(original.checks, rerun.checks)
        with self.assertRaises(ValidationError):
            self.rule.fee_basis_points = 800
            self.rule.save()

    def test_ambiguous_candidates_never_verified(self):
        records = [self.record("S1", "settlement", 100), self.record("S2", "settlement", 100), self.record("B", "bank_credit", 100)]
        decision = EvidenceMatcher().decisions(records)[-1]
        self.assertEqual(decision["state"], "ambiguous")
        self.assertEqual(len(decision["candidate_ids"]), 2)

    def test_currency_mismatch_rejected(self):
        records = self.chain() + [self.record("USD", "bank_credit", 100, currency="USD")]
        with self.assertRaises(ValidationError):
            self.reconcile(records)

    def test_nonfinal_lifecycle_blocked(self):
        records = self.chain() + [self.record("pending", "refund", 100, "P", status="pending")]
        self.assertEqual(self.reconcile(records).exception_type, "unsupported_lifecycle")

    def test_acceptance_example_has_two_distinct_breaks_not_30000(self):
        source = FinancialDataSource.objects.create(organization=self.organization, name="Zero-rate contract", source_type="payment_gateway")
        self.source = source
        ReconciliationRuleVersion.objects.create(source=source, version="zero", currency="INR", effective_from=self.time,
            fee_basis_points=0, tax_basis_points=0)
        records = [self.record("O", "order", 12840000000), self.record("P", "payment", 12840000000, "O"),
                   self.record("F", "fee", 0, "P"), self.record("T", "tax", 0, "F"),
                   self.record("R", "refund", 530000000, "P"), self.record("S", "settlement", 12309000000, "T"),
                   self.record("B", "bank_credit", 12308700000, "S"), self.record("L", "ledger_entry", 12308700000, "B")]
        case = self.reconcile(records)
        checks = {c["name"]: c for c in case.reconciliation_runs.first().checks}
        self.assertEqual(case.exception_type, "settlement_mismatch")
        self.assertEqual(case.difference_minor, -1000000)
        bank = checks["Bank credit equals settlement"]
        self.assertEqual(bank["actual_minor"] - bank["expected_minor"], -300000)
        self.assertEqual(checks["Bank credit equals general ledger"]["result"], "passed")

    def test_zero_decimal_currency_is_not_divided_by_100(self):
        from .money import format_minor
        self.assertEqual(format_minor(1234, "JPY"), "JPY 1234")
        self.assertEqual(format_minor(1234, "KWD"), "KWD 1.234")

    def test_ai_cannot_cite_another_case_in_same_organization(self):
        case = self.reconcile(self.chain())
        self.record("OTHER", "payment", 123)
        result = InvestigationAgent()._execute_tool(case, "get_transaction", {"record_id": "OTHER"})
        self.assertFalse(result["found"])

    def test_orm_and_raw_sql_cannot_change_evidence(self):
        record = self.record("P", "payment", 100)
        with self.assertRaises(ValidationError):
            record.amount_minor = 200
            record.save()
        with self.assertRaises(ValidationError):
            FinancialRecord.objects.filter(pk=record.pk).update(amount_minor=200)
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE reconciliation_financialrecord SET amount_minor = 200 WHERE id = %s", [record.pk])
        record.refresh_from_db()
        self.assertEqual(record.amount_minor, 100)

    def test_duplicate_deliveries_and_conflicting_payload_are_retained(self):
        payload = [{"external_record_id": "P", "record_type": "payment", "entity_id": "scope-1",
                    "amount_minor": 100, "occurred_at": self.time.isoformat(), "status": "captured"}]
        service = FinancialRecordIngestionService()
        for _ in range(3):
            service.ingest(self.source, "delivery", payload)
        self.assertEqual(FinancialRecord.objects.count(), 1)
        self.assertEqual(IngestionDelivery.objects.count(), 3)
        with self.assertRaises(ValidationError):
            service.ingest(self.source, "delivery", [{**payload[0], "amount_minor": 200}])
        self.assertEqual(IngestionDelivery.objects.filter(outcome="conflict").count(), 1)
        self.assertEqual(FinancialRecord.objects.get().amount_minor, 100)

    def test_ai_unavailable_retains_run_and_cannot_read_other_scope(self):
        case = self.reconcile(self.chain())
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            run = InvestigationAgent().answer(case, "Explain")
        self.assertEqual(run.model_version, "deterministic-fallback")
        self.assertIsNotNone(run.reconciliation_run_id)
        self.assertEqual(InvestigationAgent()._execute_tool(case, "get_transaction", {"record_id": "invented"})["found"], False)


    def test_ai_stays_on_original_snapshot_when_case_reruns_mid_request(self):
        records = self.chain()
        case = self.reconcile([r for r in records if r.record_type != "ledger_entry"])
        original = case.reconciliation_runs.first()
        agent = InvestigationAgent()
        agent.model_name = "test-model"
        tool_response = SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="get_check_results", input={}, id="tool-1")],
                                        usage=SimpleNamespace(input_tokens=10, output_tokens=5))
        final_response = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({
            "conclusion": "Ledger evidence is missing in the inspected snapshot.", "confidence": 0.7,
            "evidence_cited": ["B"], "sufficient_evidence": False,
            "recommended_action": "Obtain the ledger receipt."}))], usage=SimpleNamespace(input_tokens=20, output_tokens=15))

        def respond(**kwargs):
            if len(kwargs["messages"]) == 1:
                self.reconcile(records)
                return tool_response
            return final_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-not-real"}), patch("anthropic.Anthropic") as provider:
            provider.return_value.messages.create.side_effect = respond
            run = agent.answer(case, "Explain this case")
        case.refresh_from_db()
        self.assertEqual(case.status, "matched")
        self.assertEqual(run.reconciliation_run_id, original.pk)
        self.assertEqual((run.input_tokens, run.output_tokens, run.model_requests), (30, 20, 2))
        self.assertTrue(any(check["classification"] == "ledger_posting_missing" for check in run.tool_calls[0]["result"]))
        self.assertNotIn("raw_payload", json.dumps(run.tool_calls))

    def test_ai_rejects_unknown_tool_and_wrong_record_type(self):
        case = self.reconcile(self.chain())
        agent = InvestigationAgent()
        with self.assertRaises(ValueError):
            agent._execute_tool(case, "post_journal", {})
        self.assertFalse(agent._execute_tool(case, "get_bank_statement_line", {"record_id": "P"})["found"])

    def test_invalid_model_confidence_is_validation_error(self):
        for confidence in ["not-a-number", "NaN", "Infinity"]:
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                InvestigationAgent._parse_result(json.dumps({"conclusion": "Explanation", "confidence": confidence,
                    "evidence_cited": [], "sufficient_evidence": False}))

    def test_fallback_records_checks_without_paid_call_or_fake_confidence(self):
        case = self.reconcile(self.chain())
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            run = InvestigationAgent().answer(case, "Explain")
        self.assertEqual((run.model_requests, run.input_tokens, run.confidence), (0, 0, 0))
        self.assertIn("result", run.tool_calls[0])
        self.assertIn("No correction", run.recommended_action)


class AuthenticationControlTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="A", slug="a")
        self.other = Organization.objects.create(name="B", slug="b")
        self.user = get_user_model().objects.create_user(username="analyst")
        OrganizationMembership.objects.create(organization=self.org, user=self.user, role="viewer")

    def test_anonymous_access_denied(self):
        for url in ["/api/cases/", "/api/records/", "/api/metrics/overview/", "/api/audit-log/", "/api/ingestion/batches/"]:
            self.assertEqual(self.client.get(url, HTTP_X_ORGANIZATION_SLUG="a").status_code, 401)

    def test_header_cannot_grant_membership(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/cases/", HTTP_X_ORGANIZATION_SLUG="b").status_code, 403)
        self.assertEqual(self.client.get("/api/cases/", HTTP_X_ORGANIZATION_SLUG="a").json(), [])

    def test_viewer_cannot_ingest(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/api/ingestion/batches/", {}, HTTP_X_ORGANIZATION_SLUG="a").status_code, 403)

    def test_operational_reads_are_tenant_scoped(self):
        self.client.force_login(self.user)
        for path in ["/api/connections/", "/api/rule-versions/", "/api/identity/"]:
            self.assertEqual(self.client.get(path, HTTP_X_ORGANIZATION_SLUG="b").status_code, 403)
        identity = self.client.get("/api/identity/", HTTP_X_ORGANIZATION_SLUG="a").json()
        self.assertEqual((identity["name"], identity["role"]), ("analyst", "viewer"))

    def test_malformed_ingestion_object_returns_validation_error(self):
        OrganizationMembership.objects.filter(user=self.user).update(role="analyst")
        self.client.force_login(self.user)
        response = self.client.post("/api/ingestion/batches/", data="[]", content_type="application/json", HTTP_X_ORGANIZATION_SLUG="a")
        self.assertEqual(response.status_code, 400)

    @override_settings(DEBUG=False, LEDGERLENS_DEMO_MODE=True, SECURE_SSL_REDIRECT=False)
    def test_demo_bypass_disabled_in_production(self):
        self.assertEqual(self.client.get("/api/cases/", HTTP_X_ORGANIZATION_SLUG="ledgerlens-demo").status_code, 401)
