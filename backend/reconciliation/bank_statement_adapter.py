import csv
import io

from .models import FinancialRecordType

REQUIRED_COLUMNS = ("transaction_reference", "amount_minor", "value_date")


def parse_bank_statement_csv(csv_text: str) -> list[dict]:
    """Convert a bank statement CSV into the record dicts FinancialRecordIngestionService expects.

    Expected columns: transaction_reference, amount_minor, value_date (ISO-8601),
    and optionally narration, settlement_reference, currency.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
        raise ValueError("Duplicate column names are not supported.")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
    if missing_columns:
        raise ValueError(f"The CSV is missing required columns: {', '.join(missing_columns)}.")

    records = []
    for row_number, row in enumerate(reader, start=2):
        settlement_reference = (row.get("settlement_reference") or "").strip()
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {row_number}: column count does not match the header.")
        try:
            amount_minor = int(row["amount_minor"])
        except (TypeError, ValueError):
            amount_minor = row["amount_minor"]  # Shared ingestion retains and rejects this row.

        records.append(
            {
                "external_record_id": row["transaction_reference"].strip(),
                "record_type": FinancialRecordType.BANK_CREDIT,
                "entity_id": (row.get("entity_id") or "").strip(),
                "amount_minor": amount_minor,
                "currency": (row.get("currency") or "INR").strip().upper(),
                "occurred_at": row["value_date"].strip(),
                "reference": settlement_reference,
                "status": "processed",
                "normalization_version": "bank-csv-v1",
                "raw_payload": dict(row),
            }
        )
    return records
