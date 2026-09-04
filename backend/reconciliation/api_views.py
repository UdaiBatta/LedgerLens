from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import InvestigationAgent
from .engine import ReconciliationEngine
from .ingestion import FinancialRecordIngestionService
from .models import (
    AgentRun,
    EvidenceConnection,
    FinancialDataSource,
    FinancialRecord,
    FinancialRecordType,
    FinancialSourceType,
    IngestionBatch,
    Organization,
    ReconciliationCase,
    ReconciliationStatus,
)
from .serializers import (
    AgentRunSerializer,
    AuditLogEntrySerializer,
    FinancialRecordSerializer,
    IngestionBatchSerializer,
    ReconciliationCaseDetailSerializer,
    ReconciliationCaseListSerializer,
)

ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION_SLUG"


def require_organization(request) -> Organization:
    """Resolve the requesting organization from the X-Organization-Slug header.

    Every view scopes its queryset through this so one organization's financial
    data, cases, and audit history can never appear in another's response.
    """
    slug = request.META.get(ORGANIZATION_HEADER, "").strip()
    if not slug:
        raise DRFValidationError({"organization": "The X-Organization-Slug header is required."})
    try:
        return Organization.objects.get(slug=slug)
    except Organization.DoesNotExist as error:
        raise NotFound({"organization": "No organization matches the given slug."}) from error


class ReconciliationCaseViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"

    def get_queryset(self):
        organization = require_organization(self.request)
        queryset = ReconciliationCase.objects.filter(organization=organization).select_related(
            "organization",
            "first_break_record__source",
        ).prefetch_related(
            "check_results",
            "agent_runs",
            "evidence_connections__source_record__source",
            "evidence_connections__destination_record__source",
        )
        requested_status = self.request.query_params.get("status")
        return queryset.filter(status=requested_status) if requested_status else queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ReconciliationCaseListSerializer
        return ReconciliationCaseDetailSerializer

    @action(detail=True, methods=["get"], url_path="evidence-graph")
    def evidence_graph(self, request, public_id=None):
        reconciliation_case = self.get_object()
        connections = reconciliation_case.evidence_connections.all()
        records = {}
        edges = []
        for connection in connections:
            records[connection.source_record_id] = connection.source_record
            records[connection.destination_record_id] = connection.destination_record
            edges.append(
                {
                    "id": connection.id,
                    "source": connection.source_record_id,
                    "target": connection.destination_record_id,
                    "method": connection.match_method,
                    "confidence": connection.confidence,
                    "rationale": connection.rationale,
                    "created_by": connection.created_by,
                }
            )
        return Response(
            {
                "nodes": FinancialRecordSerializer(records.values(), many=True).data,
                "edges": edges,
            }
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, public_id=None):
        reconciliation_case = self.get_object()
        owner = str(request.data.get("owner", "Demo Operator")).strip()
        if not owner:
            return Response({"owner": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        reconciliation_case.owner = owner
        reconciliation_case.save(update_fields=["owner", "updated_at"])
        return Response(ReconciliationCaseDetailSerializer(reconciliation_case).data)

    @action(detail=True, methods=["post"])
    def ask(self, request, public_id=None):
        question = str(request.data.get("question", "")).strip()
        if not question:
            return Response(
                {"question": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        agent_run = InvestigationAgent().answer(self.get_object(), question)
        return Response(AgentRunSerializer(agent_run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def runs(self, request, public_id=None):
        return Response(AgentRunSerializer(self.get_object().agent_runs.all(), many=True).data)


class FinancialRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FinancialRecordSerializer

    def get_queryset(self):
        organization = require_organization(self.request)
        return FinancialRecord.objects.filter(source__organization=organization).select_related(
            "source", "source__organization"
        )


class OverviewMetricsView(APIView):
    def get(self, request):
        organization = require_organization(request)
        organization_records = FinancialRecord.objects.filter(source__organization=organization)
        organization_cases = ReconciliationCase.objects.filter(organization=organization)

        captured = organization_records.filter(
            record_type=FinancialRecordType.PAYMENT
        ).aggregate(total=Sum("amount_minor"))["total"] or 0
        case_counts = organization_cases.aggregate(
            total=Count("id"),
            matched=Count("id", filter=Q(status=ReconciliationStatus.MATCHED)),
            open=Count("id", filter=~Q(status=ReconciliationStatus.MATCHED)),
        )
        unexplained = sum(
            abs(reconciliation_case.difference_minor)
            for reconciliation_case in organization_cases.exclude(
                status=ReconciliationStatus.MATCHED
            )
        )
        movement = []
        for record_type in (
            FinancialRecordType.ORDER,
            FinancialRecordType.PAYMENT,
            FinancialRecordType.FEE,
            FinancialRecordType.TAX,
            FinancialRecordType.SETTLEMENT,
            FinancialRecordType.BANK_CREDIT,
            FinancialRecordType.LEDGER_ENTRY,
        ):
            summary = organization_records.filter(record_type=record_type).aggregate(
                count=Count("id"),
                amount_minor=Sum("amount_minor"),
            )
            movement.append(
                {
                    "record_type": record_type,
                    "label": FinancialRecordType(record_type).label,
                    "record_count": summary["count"],
                    "amount_minor": summary["amount_minor"] or 0,
                }
            )
        return Response(
            {
                "captured_amount_minor": captured,
                "case_count": case_counts["total"],
                "matched_case_count": case_counts["matched"],
                "open_case_count": case_counts["open"],
                "unexplained_amount_minor": unexplained,
                "movement": movement,
            }
        )


class AuditLogView(APIView):
    def get(self, request):
        organization = require_organization(request)
        agent_run_entries = [
            {
                "event_type": "agent_run",
                "occurred_at": agent_run.created_at,
                "case_reference": agent_run.reconciliation_case.case_reference,
                "case_public_id": agent_run.reconciliation_case.public_id,
                "actor": agent_run.model_version,
                "summary": f'Investigator asked "{agent_run.question}"',
                "details": {
                    "conclusion": agent_run.conclusion,
                    "confidence": str(agent_run.confidence),
                    "sufficient_evidence": agent_run.sufficient_evidence,
                    "evidence_cited": agent_run.evidence_cited,
                },
            }
            for agent_run in AgentRun.objects.filter(
                reconciliation_case__organization=organization
            ).select_related("reconciliation_case")
        ]
        evidence_connection_entries = [
            {
                "event_type": "evidence_connection",
                "occurred_at": evidence_connection.created_at,
                "case_reference": evidence_connection.reconciliation_case.case_reference,
                "case_public_id": evidence_connection.reconciliation_case.public_id,
                "actor": evidence_connection.created_by,
                "summary": (
                    f"Linked {evidence_connection.source_record.external_record_id} to "
                    f"{evidence_connection.destination_record.external_record_id} "
                    f"({evidence_connection.get_match_method_display()})"
                ),
                "details": {
                    "confidence": str(evidence_connection.confidence),
                    "matching_reason": evidence_connection.matching_reason,
                    "is_verified": evidence_connection.is_verified,
                },
            }
            for evidence_connection in EvidenceConnection.objects.filter(
                reconciliation_case__organization=organization
            ).select_related(
                "reconciliation_case", "source_record", "destination_record"
            )
        ]
        entries = sorted(
            agent_run_entries + evidence_connection_entries,
            key=lambda entry: entry["occurred_at"],
            reverse=True,
        )
        return Response(AuditLogEntrySerializer(entries, many=True).data)


class IngestionBatchView(APIView):
    def get(self, request):
        organization = require_organization(request)
        batches = IngestionBatch.objects.filter(source__organization=organization).select_related(
            "source", "source__organization"
        )[:100]
        return Response(IngestionBatchSerializer(batches, many=True).data)

    def post(self, request):
        # Ingestion is the onboarding boundary, so it may create a new organization on first
        # use — unlike every other view, which only ever reads an organization that already
        # exists. require_organization is intentionally not used here for that reason; the
        # organization_slug/header match check below provides the equivalent safety guarantee.
        requested_slug = str(request.META.get(ORGANIZATION_HEADER, "")).strip()
        if not requested_slug:
            return Response(
                {"organization": "The X-Organization-Slug header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = request.data
        required_fields = (
            "organization_slug",
            "organization_name",
            "source_name",
            "source_type",
            "batch_reference",
            "records",
        )
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            return Response(
                {"missing_fields": missing_fields},
                status=status.HTTP_400_BAD_REQUEST,
            )
        empty_fields = [
            field
            for field in (
                "organization_slug",
                "organization_name",
                "source_name",
                "batch_reference",
            )
            if not str(payload[field]).strip()
        ]
        if empty_fields:
            return Response(
                {"empty_fields": empty_fields},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(payload["records"], list) or not payload["records"]:
            return Response(
                {"records": "Provide at least one record."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payload["source_type"] not in FinancialSourceType.values:
            return Response(
                {"source_type": "Unsupported financial source type."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if str(payload["organization_slug"]).strip() != requested_slug:
            return Response(
                {"organization": "The X-Organization-Slug header must match organization_slug."},
                status=status.HTTP_403_FORBIDDEN,
            )

        organization, _ = Organization.objects.get_or_create(
            slug=requested_slug,
            defaults={"name": str(payload["organization_name"]).strip()},
        )
        source, source_created = FinancialDataSource.objects.get_or_create(
            organization=organization,
            name=str(payload["source_name"]).strip(),
            defaults={"source_type": payload["source_type"]},
        )
        if not source_created and source.source_type != payload["source_type"]:
            return Response(
                {"source_type": "The existing source uses a different source type."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            result = FinancialRecordIngestionService().ingest(
                source=source,
                batch_reference=str(payload["batch_reference"]).strip(),
                records=payload["records"],
            )
        except ValidationError as error:
            return Response(
                {"errors": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            reconciliation_case = self._reconcile_if_requested(organization, payload)
        except ValidationError as error:
            return Response(
                {
                    "batch": IngestionBatchSerializer(result.batch).data,
                    "replayed": result.replayed,
                    "reconciliation_error": (
                        error.message_dict if hasattr(error, "message_dict") else error.messages
                    ),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        response_data = {
            "batch": IngestionBatchSerializer(result.batch).data,
            "replayed": result.replayed,
            "reconciliation_case": (
                ReconciliationCaseDetailSerializer(reconciliation_case).data
                if reconciliation_case
                else None
            ),
        }
        return Response(
            response_data,
            status=status.HTTP_200_OK if result.replayed else status.HTTP_201_CREATED,
        )

    @staticmethod
    def _reconcile_if_requested(organization, payload):
        reconciliation_request = payload.get("reconcile")
        if not reconciliation_request:
            return None
        case_reference = str(reconciliation_request.get("case_reference", "")).strip()
        entity_id = str(reconciliation_request.get("entity_id", "")).strip()
        if not case_reference or not entity_id:
            raise ValidationError(
                {"reconcile": "case_reference and entity_id are required."}
            )
        records = list(
            FinancialRecord.objects.filter(
                source__organization=organization,
                entity_id=entity_id,
            )
        )
        return ReconciliationEngine().reconcile(
            organization=organization,
            case_reference=case_reference,
            entity_id=entity_id,
            records=records,
        )
