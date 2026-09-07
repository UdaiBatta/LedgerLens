from django.db import migrations


def guard_investigations(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            schema_editor.execute(f"CREATE TRIGGER reconciliation_agentrun_{operation.lower()}_guard BEFORE {operation} ON reconciliation_agentrun BEGIN SELECT RAISE(ABORT, 'LedgerLens immutable investigation'); END")
    elif schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE TRIGGER reconciliation_agentrun_guard BEFORE UPDATE OR DELETE ON reconciliation_agentrun FOR EACH ROW EXECUTE FUNCTION ledgerlens_immutable()")


def remove_guards(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        for operation in ("update", "delete"):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS reconciliation_agentrun_{operation}_guard")
    elif schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER IF EXISTS reconciliation_agentrun_guard ON reconciliation_agentrun")


class Migration(migrations.Migration):
    dependencies = [("reconciliation", "0007_agentrun_input_tokens_agentrun_latency_ms_and_more")]
    operations = [migrations.RunPython(guard_investigations, remove_guards)]
