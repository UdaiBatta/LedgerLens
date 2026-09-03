import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


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


class FinancialRecord(models.Model):
    source = models.ForeignKey(
        FinancialDataSource,
        on_delete=models.PROTECT,
        related_name="financial_records",
    )
    external_record_id = models.CharField(max_length=200)
    record_type = models.CharField(max_length=32, choices=FinancialRecordType.choices)
    direction = models.CharField(max_length=8, choices=FinancialDirection.choices)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    occurred_at = models.DateTimeField()
    content_hash = models.CharField(max_length=64)
    raw_payload = models.JSONField(default=dict)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_record_id", "content_hash"],
                name="unique_financial_record_version",
            )
        ]

    def clean(self) -> None:
        self.currency = self.currency.upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError({"currency": "Use a three-letter currency code."})

    def __str__(self) -> str:
        return f"{self.get_record_type_display()} · {self.external_record_id}"


class ReconciliationCase(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="reconciliation_cases",
    )
    case_reference = models.CharField(max_length=100)
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
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    match_method = models.CharField(max_length=32, choices=EvidenceMatchMethod.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    matching_reason = models.CharField(max_length=500)
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
