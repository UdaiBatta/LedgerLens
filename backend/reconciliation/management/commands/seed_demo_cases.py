import hashlib
import json
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from reconciliation.engine import ReconciliationEngine
from reconciliation.models import (
    FinancialDataSource,
    FinancialDirection,
    FinancialRecord,
    FinancialRecordType,
    FinancialSourceType,
    Organization,
)


DEMO_SCENARIOS = [
    {
        "case_reference": "EXC-2025-05-000150",
        "entity_id": "Nova Commerce",
        "amount": 1_200_000,
        "bank_amount": 1_183_008,
    },
    {
        "case_reference": "EXC-2025-05-000145",
        "entity_id": "Stellar Electronics",
        "amount": 1_000_000,
        "bank_amount": 985_500,
        "fuzzy_bank_link": True,
    },
    {
        "case_reference": "EXC-2025-05-000142",
        "entity_id": "Bright Retail",
        "amount": 2_500_000,
        "fee_amount": 35_000,
    },
    {
        "case_reference": "EXC-2025-05-000138",
        "entity_id": "Zenith Supplies",
        "amount": 850_000,
        "bank_delayed": True,
    },
    {
        "case_reference": "EXC-2025-05-000137",
        "entity_id": "Vertex Solutions",
        "amount": 1_500_000,
        "refund_amount": 100_000,
        "ignore_refund_in_settlement": True,
    },
    {
        "case_reference": "EXC-2025-05-000131",
        "entity_id": "Orbit Market",
        "amount": 700_000,
        "duplicate_payment_attempt": True,
    },
]


class Command(BaseCommand):
    help = "Seed deterministic LedgerLens demonstration cases."

    @transaction.atomic
    def handle(self, *args, **options):
        organization, _ = Organization.objects.get_or_create(
            slug="ledgerlens-demo",
            defaults={"name": "LedgerLens Demo"},
        )
        sources = self._get_sources(organization)
        base_time = datetime(2025, 5, 15, 10, 21, tzinfo=timezone.utc)

        for index, scenario in enumerate(DEMO_SCENARIOS):
            records = self._seed_scenario(
                sources,
                scenario,
                base_time + timedelta(days=index),
            )
            ReconciliationEngine().reconcile(
                organization,
                scenario["case_reference"],
                scenario["entity_id"],
                records,
            )

        self._seed_background_records(sources["gateway"], base_time)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(DEMO_SCENARIOS)} cases and "
                f"{FinancialRecord.objects.filter(source__organization=organization).count()} records."
            )
        )

    def _get_sources(self, organization):
        definitions = {
            "orders": ("Order System", FinancialSourceType.ORDER_SYSTEM),
            "gateway": ("Payment Gateway", FinancialSourceType.PAYMENT_GATEWAY),
            "bank": ("Settlement Bank", FinancialSourceType.BANK_ACCOUNT),
            "ledger": ("General Ledger", FinancialSourceType.GENERAL_LEDGER),
        }
        return {
            key: FinancialDataSource.objects.get_or_create(
                organization=organization,
                name=name,
                defaults={"source_type": source_type},
            )[0]
            for key, (name, source_type) in definitions.items()
        }

    def _seed_scenario(self, sources, scenario, started_at):
        case_reference = scenario["case_reference"]
        amount = scenario["amount"]
        expected_fee = (amount * 120 + 5_000) // 10_000
        fee_amount = scenario.get("fee_amount", expected_fee)
        tax_amount = (expected_fee * 1_800 + 5_000) // 10_000
        refund_amount = scenario.get("refund_amount", 0)
        settlement_refund = 0 if scenario.get("ignore_refund_in_settlement") else refund_amount
        settlement_amount = amount - settlement_refund - expected_fee - tax_amount
        bank_amount = scenario.get("bank_amount", settlement_amount)

        definitions = [
            ("orders", FinancialRecordType.ORDER, f"ORD-{case_reference[-6:]}", amount),
            ("gateway", FinancialRecordType.PAYMENT, f"PAY-{case_reference[-6:]}", amount),
            ("gateway", FinancialRecordType.FEE, f"FEE-{case_reference[-6:]}", fee_amount),
            ("gateway", FinancialRecordType.TAX, f"TAX-{case_reference[-6:]}", tax_amount),
        ]
        if refund_amount:
            definitions.append(
                ("gateway", FinancialRecordType.REFUND, f"RFN-{case_reference[-6:]}", refund_amount)
            )
        definitions.append(
            ("gateway", FinancialRecordType.SETTLEMENT, f"SET-{case_reference[-6:]}", settlement_amount)
        )
        if not scenario.get("bank_delayed"):
            definitions.append(
                ("bank", FinancialRecordType.BANK_CREDIT, f"TXN-{case_reference[-6:]}", bank_amount)
            )
        if not scenario.get("bank_delayed"):
            definitions.append(
                ("ledger", FinancialRecordType.LEDGER_ENTRY, f"JE-{case_reference[-6:]}", bank_amount)
            )

        records = []
        previous_reference = ""
        for sequence, (source_key, record_type, external_id, record_amount) in enumerate(definitions):
            linked_reference = previous_reference
            if record_type == FinancialRecordType.BANK_CREDIT and scenario.get("fuzzy_bank_link"):
                linked_reference = ""
            payload = {
                "case_reference": case_reference,
                "entity_id": scenario["entity_id"],
                "sequence": sequence,
                "linked_reference": linked_reference,
            }
            record = self._get_or_create_record(
                sources[source_key],
                external_id,
                record_type,
                scenario["entity_id"],
                record_amount,
                started_at + timedelta(minutes=sequence * 4),
                payload,
            )
            records.append(record)
            previous_reference = external_id

        if scenario.get("duplicate_payment_attempt"):
            payment = next(record for record in records if record.record_type == FinancialRecordType.PAYMENT)
            duplicate, created = FinancialRecord.objects.get_or_create(
                source=payment.source,
                record_type=payment.record_type,
                external_record_id=payment.external_record_id,
                defaults={
                    "entity_id": payment.entity_id,
                    "direction": payment.direction,
                    "amount_minor": payment.amount_minor,
                    "currency": payment.currency,
                    "occurred_at": payment.occurred_at,
                    "content_hash": payment.content_hash,
                    "raw_payload": payment.raw_payload,
                },
            )
            if created or duplicate.pk != payment.pk:
                raise RuntimeError("Duplicate payment ingestion was not idempotent.")

        return records

    def _seed_background_records(self, source, base_time):
        existing = FinancialRecord.objects.filter(source=source).count()
        for index in range(existing, 200):
            external_id = f"PAY-BACKGROUND-{index:04d}"
            self._get_or_create_record(
                source,
                external_id,
                FinancialRecordType.PAYMENT,
                f"Background Merchant {index:03d}",
                100_000 + index * 100,
                base_time - timedelta(days=index % 20, minutes=index),
                {"background_record": True, "sequence": index},
            )

    def _get_or_create_record(
        self,
        source,
        external_id,
        record_type,
        entity_id,
        amount_minor,
        occurred_at,
        payload,
    ):
        encoded_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        content_hash = hashlib.sha256(encoded_payload).hexdigest()
        direction = (
            FinancialDirection.DEBIT
            if record_type in {
                FinancialRecordType.FEE,
                FinancialRecordType.TAX,
                FinancialRecordType.REFUND,
            }
            else FinancialDirection.CREDIT
        )
        return FinancialRecord.objects.get_or_create(
            source=source,
            record_type=record_type,
            external_record_id=external_id,
            defaults={
                "batch_id": "DEMO-2025-05",
                "entity_id": entity_id,
                "direction": direction,
                "amount_minor": amount_minor,
                "currency": "INR",
                "occurred_at": occurred_at,
                "status": "processed",
                "reference": payload.get("linked_reference", ""),
                "content_hash": content_hash,
                "raw_payload": payload,
            },
        )[0]
