from datetime import datetime, timezone
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from reconciliation.engine import ReconciliationEngine
from reconciliation.ingestion import FinancialRecordIngestionService
from reconciliation.models import FinancialDataSource, Organization, ReconciliationRuleVersion, FinancialRecord


class Command(BaseCommand):
    help = "Create a replay-safe settlement batch and GL exceptions using actual ingestion and controls."

    def add_arguments(self, parser):
        parser.add_argument("--payments", type=int, default=500)

    def handle(self, *args, **options):
        count = options["payments"]
        if not 1 <= count <= 1000:
            raise CommandError("Use 1 to 1000 payments for the bounded synchronous benchmark.")
        started = perf_counter()
        org, _ = Organization.objects.get_or_create(slug="ledgerlens-demo", defaults={"name": "LedgerLens Demo"})
        gateway, _ = FinancialDataSource.objects.get_or_create(organization=org, name="Control Gateway", defaults={"source_type": "payment_gateway"})
        bank, _ = FinancialDataSource.objects.get_or_create(organization=org, name="Control Bank", defaults={"source_type": "bank_account"})
        ledger, _ = FinancialDataSource.objects.get_or_create(organization=org, name="Control ERP", defaults={"source_type": "general_ledger"})
        at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        ReconciliationRuleVersion.objects.get_or_create(source=gateway, version="control-v1", defaults={
            "currency": "INR", "effective_from": at, "fee_basis_points": 120, "tax_basis_points": 1800})
        for scenario, size in [(f"BATCH-{count}", count), ("GL-MISSING", 1), ("GL-MISMATCH", 1)]:
            def row(identifier, kind, amount, reference="", contributors=None):
                return {"external_record_id": f"{scenario}-{identifier}", "record_type": kind,
                        "entity_id": scenario, "amount_minor": amount, "currency": "INR", "status": "processed",
                        "reference": f"{scenario}-{reference}" if reference else "", "occurred_at": at.isoformat(),
                        "raw_payload": {"synthetic": True, "contributing_references": contributors or []}}
            feed = []
            for i in range(size):
                feed += [row(f"O{i}", "order", 100000), row(f"P{i}", "payment", 100000, f"O{i}"),
                         row(f"F{i}", "fee", 1200, f"P{i}"), row(f"T{i}", "tax", 216, f"F{i}")]
            expected = size * 98584
            feed.append(row("S", "settlement", expected, contributors=[f"{scenario}-T{i}" for i in range(size)]))
            service = FinancialRecordIngestionService()
            service.ingest(gateway, scenario, feed)
            service.ingest(bank, scenario, [row("B", "bank_credit", expected, "S")])
            if scenario != "GL-MISSING":
                service.ingest(ledger, scenario, [row("L", "ledger_entry", expected - (500 if scenario == "GL-MISMATCH" else 0), "B")])
            case = ReconciliationEngine().reconcile(org, scenario, scenario,
                list(FinancialRecord.objects.filter(source__organization=org, entity_id=scenario)))
            self.stdout.write(f"{scenario}: {case.exception_type}; expected={case.expected_amount_minor}, observed={case.actual_amount_minor} minor units")
        self.stdout.write(f"Elapsed ingestion + reconciliation: {perf_counter() - started:.3f}s (local measurement, not a scale claim)")
