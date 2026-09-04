from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from reconciliation.bank_statement_adapter import parse_bank_statement_csv
from reconciliation.engine import ReconciliationEngine
from reconciliation.ingestion import FinancialRecordIngestionService
from reconciliation.models import FinancialDataSource, FinancialRecord, FinancialSourceType, Organization


class Command(BaseCommand):
    help = "Import a bank statement CSV through the shared ingestion service and optionally reconcile it."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--organization-slug", required=True)
        parser.add_argument("--organization-name", required=False)
        parser.add_argument("--source-name", required=True)
        parser.add_argument("--batch-reference", required=True)
        parser.add_argument(
            "--reconcile-entity",
            required=False,
            help="If set, run the reconciliation engine for this entity_id after import.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.is_file():
            raise CommandError(f"No such file: {csv_path}")

        try:
            records = parse_bank_statement_csv(csv_path.read_text(encoding="utf-8-sig"))
        except ValueError as error:
            raise CommandError(str(error)) from error

        organization, _ = Organization.objects.get_or_create(
            slug=options["organization_slug"],
            defaults={"name": options.get("organization_name") or options["organization_slug"]},
        )
        source, _ = FinancialDataSource.objects.get_or_create(
            organization=organization,
            name=options["source_name"],
            defaults={"source_type": FinancialSourceType.BANK_ACCOUNT},
        )

        try:
            result = FinancialRecordIngestionService().ingest(
                source=source,
                batch_reference=options["batch_reference"],
                records=records,
            )
        except ValidationError as error:
            raise CommandError(str(error)) from error

        if result.replayed:
            self.stdout.write(
                self.style.WARNING(
                    f"Batch {result.batch.batch_reference} was already imported "
                    f"({result.batch.imported_count} imported, "
                    f"{result.batch.duplicate_count} duplicate, "
                    f"{result.batch.rejected_count} rejected); no new records were created."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Batch {result.batch.batch_reference}: "
                    f"{result.batch.imported_count} imported, "
                    f"{result.batch.duplicate_count} duplicate, "
                    f"{result.batch.rejected_count} rejected."
                )
            )
        for error in result.batch.errors:
            self.stdout.write(self.style.WARNING(f"  row {error['index']}: {error['reason']}"))

        entity_id = options.get("reconcile_entity")
        if not entity_id:
            return

        entity_records = list(
            FinancialRecord.objects.filter(
                source__organization=organization,
                entity_id=entity_id,
            ).select_related("source")
        )
        if not entity_records:
            self.stdout.write(self.style.WARNING(f"No records found for entity_id={entity_id}."))
            return

        reconciliation_case = ReconciliationEngine().reconcile(
            organization=organization,
            case_reference=options["batch_reference"],
            entity_id=entity_id,
            records=entity_records,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciled {reconciliation_case.case_reference}: {reconciliation_case.exception_type} "
                f"({reconciliation_case.status})"
            )
        )
