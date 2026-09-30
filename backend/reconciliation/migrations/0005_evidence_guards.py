from django.db import migrations
import hashlib
import json


TABLES = ["financialrecord", "reconciliationrun", "reconciliationruleversion", "auditevent", "ingestiondelivery"]


def install_guards(apps, schema_editor):
    record_model = apps.get_model("reconciliation", "FinancialRecord")
    for record in record_model.objects.using(schema_editor.connection.alias).iterator():
        values = {f.attname: getattr(record, f.attname) for f in record._meta.concrete_fields
                  if f.name not in {"id", "ingested_at", "normalized_hash"}}
        digest = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        record_model.objects.using(schema_editor.connection.alias).filter(pk=record.pk).update(normalized_hash=digest)
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute("CREATE FUNCTION ledgerlens_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'LedgerLens immutable evidence'; END; $$")
    for table in TABLES:
        name = "reconciliation_" + table
        if vendor == "sqlite":
            for operation in ("UPDATE", "DELETE"):
                schema_editor.execute(f"CREATE TRIGGER {name}_{operation.lower()}_guard BEFORE {operation} ON {name} BEGIN SELECT RAISE(ABORT, 'LedgerLens immutable evidence'); END")
        elif vendor == "postgresql":
            schema_editor.execute(f"CREATE TRIGGER {name}_guard BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION ledgerlens_immutable()")


def remove_guards(apps, schema_editor):
    for table in TABLES:
        name = "reconciliation_" + table
        if schema_editor.connection.vendor == "sqlite":
            for operation in ("update", "delete"):
                schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}_{operation}_guard")
        elif schema_editor.connection.vendor == "postgresql":
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}_guard ON {name}")
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP FUNCTION IF EXISTS ledgerlens_immutable()")


class Migration(migrations.Migration):
    dependencies = [("reconciliation", "0004_financial_controls")]
    operations = [migrations.RunPython(install_guards, remove_guards)]
