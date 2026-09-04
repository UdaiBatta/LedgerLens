import hashlib
import json
from dataclasses import dataclass
from datetime import timezone as datetime_timezone

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    FinancialDataSource,
    FinancialDirection,
    FinancialRecord,
    FinancialRecordType,
    IngestionBatch,
    IngestionBatchStatus,
)


@dataclass(frozen=True)
class IngestionResult:
    batch: IngestionBatch
    imported_records: list[FinancialRecord]
    replayed: bool


class FinancialRecordIngestionService:
    debit_record_types = {
        FinancialRecordType.FEE,
        FinancialRecordType.TAX,
        FinancialRecordType.REFUND,
    }

    @transaction.atomic
    def ingest(
        self,
        source: FinancialDataSource,
        batch_reference: str,
        records: list[dict],
    ) -> IngestionResult:
        if not batch_reference.strip():
            raise ValidationError({"batch_reference": "This field is required."})
        if not isinstance(records, list) or not records:
            raise ValidationError({"records": "Provide at least one record."})

        batch_hash = self._hash(records)
        existing_batch = IngestionBatch.objects.filter(
            source=source,
            batch_reference=batch_reference,
        ).first()
        if existing_batch:
            if existing_batch.content_hash != batch_hash:
                raise ValidationError(
                    {"batch_reference": "This batch reference was already used for different data."}
                )
            return IngestionResult(existing_batch, [], True)

        batch = IngestionBatch.objects.create(
            source=source,
            batch_reference=batch_reference,
            content_hash=batch_hash,
            received_count=len(records),
        )
        imported_records = []
        duplicate_count = 0
        errors = []

        for index, source_record in enumerate(records):
            try:
                record, created = self._ingest_record(source, batch_reference, source_record)
                if created:
                    imported_records.append(record)
                else:
                    duplicate_count += 1
            except (KeyError, TypeError, ValueError, ValidationError) as error:
                errors.append(
                    {
                        "index": index,
                        "external_record_id": str(source_record.get("external_record_id", ""))
                        if isinstance(source_record, dict)
                        else "",
                        "reason": self._error_message(error),
                    }
                )

        batch.imported_count = len(imported_records)
        batch.duplicate_count = duplicate_count
        batch.rejected_count = len(errors)
        batch.errors = errors
        batch.status = self._batch_status(len(imported_records), len(errors))
        batch.completed_at = timezone.now()
        batch.save(
            update_fields=[
                "imported_count",
                "duplicate_count",
                "rejected_count",
                "errors",
                "status",
                "completed_at",
            ]
        )
        return IngestionResult(batch, imported_records, False)

    def _ingest_record(self, source, batch_reference, source_record):
        if not isinstance(source_record, dict):
            raise TypeError("Each record must be an object.")

        external_record_id = str(source_record["external_record_id"]).strip()
        record_type = str(source_record["record_type"]).strip()
        entity_id = str(source_record["entity_id"]).strip()
        if not external_record_id or not entity_id:
            raise ValueError("external_record_id and entity_id cannot be empty.")
        if record_type not in FinancialRecordType.values:
            raise ValueError(f"Unsupported record_type: {record_type}.")

        amount_minor = source_record["amount_minor"]
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor < 0:
            raise ValueError("amount_minor must be a non-negative integer.")

        occurred_at = parse_datetime(str(source_record["occurred_at"]))
        if not occurred_at:
            raise ValueError("occurred_at must be an ISO-8601 datetime.")
        if timezone.is_naive(occurred_at):
            occurred_at = timezone.make_aware(occurred_at, datetime_timezone.utc)

        raw_payload = source_record.get("raw_payload", source_record)
        if not isinstance(raw_payload, dict):
            raise ValueError("raw_payload must be an object.")
        content_hash = self._hash(raw_payload)
        direction = str(source_record.get("direction", "")).strip() or (
            FinancialDirection.DEBIT
            if record_type in self.debit_record_types
            else FinancialDirection.CREDIT
        )
        fee_minor = self._optional_minor_amount(source_record, "fee_minor")
        tax_minor = self._optional_minor_amount(source_record, "tax_minor")
        currency = str(source_record.get("currency", "INR")).upper()
        record_status = str(source_record.get("status", ""))
        reference = str(source_record.get("reference", ""))
        existing_record = FinancialRecord.objects.filter(
            source=source,
            record_type=record_type,
            external_record_id=external_record_id,
        ).first()
        if existing_record:
            normalized_values = (
                entity_id,
                direction,
                amount_minor,
                fee_minor,
                tax_minor,
                currency,
                occurred_at,
                record_status,
                reference,
            )
            existing_values = (
                existing_record.entity_id,
                existing_record.direction,
                existing_record.amount_minor,
                existing_record.fee_minor,
                existing_record.tax_minor,
                existing_record.currency,
                existing_record.occurred_at,
                existing_record.status,
                existing_record.reference,
            )
            if existing_record.content_hash != content_hash or existing_values != normalized_values:
                raise ValidationError(
                    "The record identifier already exists with different immutable evidence."
                )
            return existing_record, False

        record = FinancialRecord(
            source=source,
            external_record_id=external_record_id,
            batch_id=batch_reference,
            record_type=record_type,
            entity_id=entity_id,
            direction=direction,
            amount_minor=amount_minor,
            fee_minor=fee_minor,
            tax_minor=tax_minor,
            currency=currency,
            occurred_at=occurred_at,
            status=record_status,
            reference=reference,
            content_hash=content_hash,
            raw_payload=raw_payload,
        )
        record.full_clean()
        record.save()
        return record, True

    @staticmethod
    def _optional_minor_amount(source_record, field_name):
        value = source_record.get(field_name, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")
        return value

    @staticmethod
    def _hash(value) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _error_message(error) -> str:
        if isinstance(error, ValidationError):
            return "; ".join(error.messages)
        return str(error)

    @staticmethod
    def _batch_status(imported_count, rejected_count):
        if rejected_count == 0:
            return IngestionBatchStatus.PROCESSED
        if imported_count:
            return IngestionBatchStatus.PARTIAL
        return IngestionBatchStatus.REJECTED
