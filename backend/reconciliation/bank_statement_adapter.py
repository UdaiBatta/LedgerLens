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
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
    if missing_columns:
        raise ValueError(f"The CSV is missing required columns: {', '.join(missing_columns)}.")

    records = []
    for row_number, row in enumerate(reader, start=2):
        narration = (row.get("narration") or "").strip()
        settlement_reference = (row.get("settlement_reference") or "").strip()
        try:
            amount_minor = int(row["amount_minor"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Row {row_number}: amount_minor must be an integer.") from error

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
                "raw_payload": {
                    "transaction_reference": row["transaction_reference"].strip(),
                    "amount_minor": amount_minor,
                    "value_date": row["value_date"].strip(),
                    "narration": narration,
                    "linked_reference": settlement_reference,
                },
            }
        )
    return records
