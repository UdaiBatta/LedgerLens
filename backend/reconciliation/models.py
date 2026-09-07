import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from .immutability import AppendOnlyModel, content_digest
from .money import validate_currency


class FinancialSourceType(models.TextChoices):
    ORDER_SYSTEM = "order_system", "Order system"
    PAYMENT_GATEWAY = "payment_gateway", "Payment gateway"
    BANK_ACCOUNT = "bank_account", "Bank account"
    GENERAL_LEDGER = "general_ledger", "General ledger"
    TAX_SYSTEM = "tax_system", "Tax system"


class FinancialRecordType(models.TextChoices):
    ORDER = "order", "Order"
    PAYMENT = "payment", "Payment"
    FEE = "fee", "Fee"
    TAX = "tax", "Tax"
    REFUND = "refund", "Refund"
    SETTLEMENT = "settlement", "Settlement"
    BANK_CREDIT = "bank_credit", "Bank credit"
    LEDGER_ENTRY = "ledger_entry", "Ledger entry"


class FinancialDirection(models.TextChoices):
    CREDIT = "credit", "Credit"
    DEBIT = "debit", "Debit"


class ReconciliationStatus(models.TextChoices):
    OPEN = "open", "Open"
    MATCHED = "matched", "Matched"
    NEEDS_REVIEW = "needs_review", "Needs review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence", "Insufficient evidence"


class EvidenceMatchMethod(models.TextChoices):
    EXACT_REFERENCE = "exact_reference", "Exact reference"
    SOURCE_REFERENCE = "source_reference", "Source reference"
    AMOUNT_AND_TIME = "amount_and_time", "Amount and time"
    MANUAL_REVIEW = "manual_review", "Manual review"


class EvidenceCreatedBy(models.TextChoices):
    RULES_ENGINE = "rules_engine", "Rules engine"
    HUMAN = "human", "Human"


class CheckResultStatus(models.TextChoices):
    PASSED = "passed", "Passed"
    FAILED = "failed", "Failed"
    WAITING = "waiting", "Waiting"


class IngestionBatchStatus(models.TextChoices):
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    PARTIAL = "partial", "Partially processed"
    REJECTED = "rejected", "Rejected"


class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class FinancialDataSource(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="financial_data_sources",
    )
    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=32, choices=FinancialSourceType.choices)
    external_account_reference = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_data_source_name_per_organization",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} · {self.name}"


class FinancialRecord(AppendOnlyModel):
    source = models.ForeignKey(
        FinancialDataSource,
        on_delete=models.PROTECT,
        related_name="financial_records",
    )
    external_record_id = models.CharField(max_length=200)
    batch_id = models.CharField(max_length=100, blank=True)
    record_type = models.CharField(max_length=32, choices=FinancialRecordType.choices)
    entity_id = models.CharField(max_length=200, default="")
    direction = models.CharField(max_length=8, choices=FinancialDirection.choices)
    amount_minor = models.PositiveBigIntegerField()
    fee_minor = models.PositiveBigIntegerField(default=0)
    tax_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3)
    occurred_at = models.DateTimeField()
    status = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=200, blank=True)
    content_hash = models.CharField(max_length=64)
    raw_payload = models.JSONField(default=dict)
    ingested_at = models.DateTimeField(auto_now_add=True)
    normalization_version = models.CharField(max_length=40, default="canonical-v1")
    normalized_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "record_type", "external_record_id"],
                name="unique_financial_source_record",
            )
        ]

    def clean(self) -> None:
        self.currency = self.currency.upper()
        validate_currency(self.currency)
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError({"currency": "Use a three-letter currency code."})

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            self.normalized_hash = content_digest({
                field.attname: getattr(self, field.attname)
                for field in self._meta.concrete_fields
                if field.name not in {"id", "ingested_at", "normalized_hash"}
            })
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_record_type_display()} · {self.external_record_id}"


class IngestionBatch(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source = models.ForeignKey(
        FinancialDataSource,
        on_delete=models.PROTECT,
        related_name="ingestion_batches",
    )
    batch_reference = models.CharField(max_length=100)
    content_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=IngestionBatchStatus.choices,
        default=IngestionBatchStatus.PROCESSING,
    )
    received_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "batch_reference"],
                name="unique_ingestion_batch_per_source",
            )
        ]

    def __str__(self) -> str:
        return f"{self.source.name} · {self.batch_reference}"


class ReconciliationCase(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="reconciliation_cases",
    )
    case_reference = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=200, default="")
    exception_type = models.CharField(max_length=100, default="")
    status = models.CharField(
        max_length=32,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.OPEN,
    )
    currency = models.CharField(max_length=3)
    expected_amount_minor = models.BigIntegerField()
    actual_amount_minor = models.BigIntegerField()
    first_break_record = models.ForeignKey(
        FinancialRecord,
        on_delete=models.SET_NULL,
        related_name="first_break_cases",
        blank=True,
        null=True,
    )
    owner = models.CharField(max_length=200, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    workflow_status = models.CharField(max_length=32, default="unassigned")
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "case_reference"],
                name="unique_case_reference_per_organization",
            )
        ]

    @property
    def difference_minor(self) -> int:
        return self.actual_amount_minor - self.expected_amount_minor

    def clean(self) -> None:
        self.currency = self.currency.upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError({"currency": "Use a three-letter currency code."})
        if (
            self.first_break_record_id
            and self.first_break_record.source.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"first_break_record": "The first-break record must belong to this organization."}
            )

    def __str__(self) -> str:
        return self.case_reference


class EvidenceConnection(models.Model):
    reconciliation_case = models.ForeignKey(
        ReconciliationCase,
        on_delete=models.CASCADE,
        related_name="evidence_connections",
    )
    source_record = models.ForeignKey(
        FinancialRecord,
        on_delete=models.PROTECT,
        related_name="outgoing_evidence_connections",
    )
    destination_record = models.ForeignKey(
        FinancialRecord,
        on_delete=models.PROTECT,
        related_name="incoming_evidence_connections",
    )
    sequence_number = models.PositiveSmallIntegerField()
    link_type = models.CharField(max_length=50, default="transaction_flow")
    match_method = models.CharField(max_length=32, choices=EvidenceMatchMethod.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    matching_reason = models.CharField(max_length=500)
    rationale = models.JSONField(default=dict)
    created_by = models.CharField(
        max_length=20,
        choices=EvidenceCreatedBy.choices,
        default=EvidenceCreatedBy.RULES_ENGINE,
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence_number", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(source_record=F("destination_record")),
                name="evidence_connection_cannot_link_record_to_itself",
            ),
            models.CheckConstraint(
                condition=Q(confidence__gte=0) & Q(confidence__lte=1),
                name="evidence_confidence_between_zero_and_one",
            ),
            models.UniqueConstraint(
                fields=["reconciliation_case", "sequence_number"],
                name="unique_evidence_sequence_per_case",
            ),
        ]

    def clean(self) -> None:
        organization_id = self.reconciliation_case.organization_id
        if self.source_record.source.organization_id != organization_id:
            raise ValidationError(
                {"source_record": "The source record must belong to this organization."}
            )
        if self.destination_record.source.organization_id != organization_id:
            raise ValidationError(
                {"destination_record": "The destination record must belong to this organization."}
            )

    def __str__(self) -> str:
        return (
            f"{self.reconciliation_case.case_reference}: "
            f"{self.source_record.external_record_id} → "
            f"{self.destination_record.external_record_id}"
        )


class CheckResult(models.Model):
    reconciliation_case = models.ForeignKey(
        ReconciliationCase,
        on_delete=models.CASCADE,
        related_name="check_results",
    )
    check_name = models.CharField(max_length=120)
    result = models.CharField(max_length=12, choices=CheckResultStatus.choices)
    evidence = models.JSONField(default=list)
    details = models.CharField(max_length=500, blank=True)
    ran_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["reconciliation_case", "check_name"],
                name="unique_check_name_per_case",
            )
        ]

    def __str__(self) -> str:
        return f"{self.reconciliation_case.case_reference} · {self.check_name}"


class AgentRun(models.Model):
    reconciliation_case = models.ForeignKey(
        ReconciliationCase,
        on_delete=models.CASCADE,
        related_name="agent_runs",
    )
    question = models.TextField()
    tool_calls = models.JSONField(default=list)
    conclusion = models.TextField()
    recommended_action = models.TextField(blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    evidence_cited = models.JSONField(default=list)
    sufficient_evidence = models.BooleanField()
    model_version = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=40, default="investigation-v2")
    fallback_reason = models.CharField(max_length=100, blank=True)
    reconciliation_run = models.ForeignKey("ReconciliationRun", null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.reconciliation_case.case_reference} · {self.created_at:%Y-%m-%d %H:%M}"


class OrganizationMembership(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[(r, r.title()) for r in ("viewer", "analyst", "manager", "administrator", "auditor")])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "user"], name="unique_organization_membership")]


class ReconciliationRuleVersion(AppendOnlyModel):
    source = models.ForeignKey(FinancialDataSource, on_delete=models.PROTECT, related_name="rule_versions")
    version = models.CharField(max_length=64)
    currency = models.CharField(max_length=3)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    fee_basis_points = models.PositiveIntegerField()
    tax_basis_points = models.PositiveIntegerField()
    refund_policy = models.CharField(max_length=32, default="deduct_processed", choices=[("deduct_processed", "Deduct processed refunds"), ("external", "Refunds settled separately")])
    bank_wait_hours = models.PositiveIntegerField(default=48)
    settlement_wait_hours = models.PositiveIntegerField(default=48)
    tolerance_minor = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "version"], name="unique_source_rule_version")]

    def save(self, *args, **kwargs):
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValidationError("Rule effective_until must follow effective_from.")
        validate_currency(self.currency)
        if self.fee_basis_points > 10000 or self.tax_basis_points > 10000:
            raise ValidationError("Percentage rates above 100% are outside this rule model.")
        self.full_clean()
        super().save(*args, **kwargs)


class ReconciliationRun(AppendOnlyModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    reconciliation_case = models.ForeignKey(ReconciliationCase, on_delete=models.PROTECT, related_name="reconciliation_runs")
    as_of = models.DateTimeField()
    engine_version = models.CharField(max_length=40, default="control-v2")
    inputs = models.JSONField()
    rules = models.JSONField()
    decisions = models.JSONField()
    checks = models.JSONField()
    result = models.JSONField()
    source_watermarks = models.JSONField()
    input_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class AuditEvent(AppendOnlyModel):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    reconciliation_case = models.ForeignKey(ReconciliationCase, on_delete=models.PROTECT, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    event_type = models.CharField(max_length=64)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class IngestionDelivery(AppendOnlyModel):
    source = models.ForeignKey(FinancialDataSource, on_delete=models.PROTECT)
    batch_reference = models.CharField(max_length=100)
    content_hash = models.CharField(max_length=64)
    payload = models.JSONField()
    outcome = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
