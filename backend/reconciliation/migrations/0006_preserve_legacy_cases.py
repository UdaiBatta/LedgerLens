"""Retain the pre-upgrade projection without pretending old rules were versioned."""
import hashlib
import json

from django.db import migrations
from django.utils import timezone


def preserve_legacy_cases(apps, schema_editor):
    alias = schema_editor.connection.alias
    Case = apps.get_model("reconciliation", "ReconciliationCase")
    Record = apps.get_model("reconciliation", "FinancialRecord")
    Connection = apps.get_model("reconciliation", "EvidenceConnection")
    Check = apps.get_model("reconciliation", "CheckResult")
    Run = apps.get_model("reconciliation", "ReconciliationRun")
    Audit = apps.get_model("reconciliation", "AuditEvent")
    captured_at = timezone.now()

    for case in Case.objects.using(alias).iterator():
        if Run.objects.using(alias).filter(reconciliation_case_id=case.pk).exists():
            continue
        edges = list(Connection.objects.using(alias).filter(reconciliation_case_id=case.pk).values())
        record_ids = {edge[key] for edge in edges for key in ("source_record_id", "destination_record_id")}
        if case.first_break_record_id:
            record_ids.add(case.first_break_record_id)
        inputs = json.loads(json.dumps(list(Record.objects.using(alias).filter(pk__in=record_ids).order_by("id").values()), default=str))
        checks = [{"name": check.check_name, "result": check.result, "evidence": check.evidence, "details": check.details}
                  for check in Check.objects.using(alias).filter(reconciliation_case_id=case.pk)]
        run = Run.objects.using(alias).create(
            reconciliation_case_id=case.pk, as_of=captured_at, engine_version="legacy-snapshot",
            inputs=inputs, rules=[], decisions=json.loads(json.dumps(edges, default=str)), checks=checks,
            result={"status": case.status, "exception_type": case.exception_type, "currency": case.currency,
                    "expected_amount_minor": case.expected_amount_minor, "actual_amount_minor": case.actual_amount_minor,
                    "amounts_known": False, "difference_minor": None,
                    "limitation": "Upgrade-time snapshot only; original rules, inputs and execution time cannot be reconstructed."},
            source_watermarks={}, input_hash=hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
        )
        Audit.objects.using(alias).create(organization_id=case.organization_id, reconciliation_case_id=case.pk,
            event_type="legacy_snapshot_preserved", after={"run_id": str(run.public_id)},
            reason="Preserved current projection at upgrade; not a reconstructed historical execution.")


class Migration(migrations.Migration):
    dependencies = [("reconciliation", "0005_evidence_guards")]
    operations = [migrations.RunPython(preserve_legacy_cases, migrations.RunPython.noop)]
