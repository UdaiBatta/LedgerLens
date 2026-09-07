from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum, Max, Prefetch
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import InvestigationAgent
from .access import require_organization
from .engine import ReconciliationEngine
from .ingestion import FinancialRecordIngestionService
from .models import (
    AgentRun,
    AuditEvent,
    EvidenceConnection,
    ReconciliationRun,
    ReconciliationRuleVersion,
    FinancialDataSource,
    FinancialRecord,
    FinancialRecordType,
    FinancialSourceType,
    IngestionBatch,
    ReconciliationCase,
    ReconciliationStatus,
)
from .serializers import (
    AgentRunSerializer,
    FinancialRecordSerializer,
    IngestionBatchSerializer,
    ReconciliationCaseDetailSerializer,
    ReconciliationCaseListSerializer,
)

ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION_SLUG"


class ReconciliationCaseViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"

    def get_queryset(self):
        organization = require_organization(self.request)
        queryset = ReconciliationCase.objects.filter(organization=organization).select_related(
            "organization",
            "first_break_record__source",
        )
        queryset = queryset.prefetch_related(Prefetch(
            "reconciliation_runs",
            queryset=ReconciliationRun.objects.only("id", "result", "reconciliation_case_id").order_by("-id")[:1],
            to_attr="latest_runs",
        ))
        if self.action != "list":
            # Join each edge's records instead of constructing a large OR expression
            # for every record in a settlement when prefetching nested relationships.
            queryset = queryset.prefetch_related(
                "check_results", "agent_runs",
                Prefetch("evidence_connections", queryset=EvidenceConnection.objects.select_related(
                    "source_record__source", "destination_record__source")),
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
        latest = reconciliation_case.reconciliation_runs.first()
        if latest:
            records = {r.pk: r for r in FinancialRecord.objects.filter(pk__in=[item["id"] for item in latest.inputs]).select_related("source")}
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
    @transaction.atomic
    def assign(self, request, public_id=None):
        reconciliation_case = self.get_object()
        actor = request.user if request.user.is_authenticated else None
        owner = actor.get_full_name() or actor.get_username() if actor else "Demo Operator"
        before = {"owner": reconciliation_case.owner, "assigned_to_id": reconciliation_case.assigned_to_id}
        reconciliation_case.assigned_to = actor
        reconciliation_case.owner = owner
        reconciliation_case.workflow_status = "investigating"
        reconciliation_case.save(update_fields=["owner", "assigned_to", "workflow_status", "updated_at"])
        AuditEvent.objects.create(organization=reconciliation_case.organization, reconciliation_case=reconciliation_case,
                                  actor=actor, event_type="case_assigned", before=before,
                                  after={"owner": owner, "assigned_to_id": reconciliation_case.assigned_to_id})
        return Response(ReconciliationCaseDetailSerializer(reconciliation_case).data)

    @action(detail=True, methods=["get"], url_path="reconciliation-runs")
    def reconciliation_runs(self, request, public_id=None):
        return Response(list(self.get_object().reconciliation_runs.values()[:100]))

    @action(detail=True, methods=["post"], url_path="workflow")
    @transaction.atomic
    def workflow(self, request, public_id=None):
        case = self.get_object()
        if not isinstance(request.data, dict):
            raise DRFValidationError("Provide a JSON object.")
        workflow = request.data.get("status")
        reason = str(request.data.get("reason", "")).strip()
        allowed = {"investigating", "waiting_for_source", "waiting_for_bank", "resolved", "accepted_variance", "false_positive"}
        if workflow not in allowed or not reason:
            raise DRFValidationError("Provide a supported workflow status and a reason.")
        if workflow in {"resolved", "accepted_variance", "false_positive"} and request.membership.role not in {"manager", "administrator"}:
            return Response({"detail": "A manager must close a case."}, status=403)
        before = {"workflow_status": case.workflow_status}
        case.workflow_status = workflow
        case.save(update_fields=["workflow_status", "updated_at"])
        AuditEvent.objects.create(organization=case.organization, reconciliation_case=case, actor=request.user,
                                  event_type="status_changed", before=before, after={"workflow_status": workflow}, reason=reason[:2000])
        return Response(ReconciliationCaseDetailSerializer(case).data)

    @action(detail=True, methods=["post"])
    def ask(self, request, public_id=None):
        question = request.data.get("question") if isinstance(request.data, dict) else None
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            return Response(
                {"question": "Provide 1 to 2000 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        agent_run = InvestigationAgent().answer(self.get_object(), question.strip())
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
        currency = request.query_params.get("currency", "INR").upper()
        organization_records = FinancialRecord.objects.filter(source__organization=organization, currency=currency)
        organization_cases = ReconciliationCase.objects.filter(organization=organization, currency=currency)

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
            for reconciliation_case in organization_cases.filter(status=ReconciliationStatus.NEEDS_REVIEW)
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
                "currency": currency,
                "source_count": organization.financial_data_sources.count(),
                "fresh_source_count": organization.financial_data_sources.filter(financial_records__ingested_at__gte=timezone.now() - timedelta(hours=24)).distinct().count(),
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
        events = AuditEvent.objects.filter(organization=organization, reconciliation_case__isnull=False).select_related("reconciliation_case", "actor")[:500]
        return Response([{
            "event_type": event.event_type, "occurred_at": event.created_at,
            "case_reference": event.reconciliation_case.case_reference,
            "case_public_id": event.reconciliation_case.public_id,
            "actor": event.actor.get_username() if event.actor else "system",
            "summary": event.event_type.replace("_", " "),
            "details": {"before": event.before, "after": event.after, "reason": event.reason, "correlation_id": str(event.correlation_id)},
        } for event in events])


class IngestionBatchView(APIView):
    def get(self, request):
        organization = require_organization(request)
        batches = IngestionBatch.objects.filter(source__organization=organization).select_related(
            "source", "source__organization"
        )[:100]
        return Response(IngestionBatchSerializer(batches, many=True).data)

    def post(self, request):
        # Membership authorizes access; the header only selects that organization.
        requested_slug = str(request.META.get(ORGANIZATION_HEADER, "")).strip()
        if not requested_slug:
            return Response(
                {"organization": "The X-Organization-Slug header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = request.data
        if not isinstance(payload, dict):
            raise DRFValidationError("Provide a JSON object.")
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
            if not isinstance(payload[field], str) or not payload[field].strip()
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

        organization = require_organization(request)
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
        if not isinstance(reconciliation_request, dict):
            raise ValidationError("reconcile must be an object.")
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


class IdentityView(APIView):
    def get(self, request):
        return Response({"organization": request.organization.slug,
                         "name": (request.user.get_full_name() or request.user.get_username()) if request.user.is_authenticated else "Demo Operator",
                         "role": request.membership.role if request.membership else "demo"})


class ConnectionStatusView(APIView):
    def get(self, request):
        sources = FinancialDataSource.objects.filter(organization=require_organization(request)).annotate(
            last_record_at=Max("financial_records__ingested_at"), record_count=Count("financial_records"))
        return Response([{"id": source.pk, "name": source.name, "type": source.source_type,
                          "last_record_at": source.last_record_at, "record_count": source.record_count,
                          "state": "no_data" if not source.last_record_at else "fresh" if source.last_record_at >= timezone.now() - timedelta(hours=24) else "stale"}
                         for source in sources[:100]])


class RuleVersionView(APIView):
    def get(self, request):
        return Response(list(ReconciliationRuleVersion.objects.filter(source__organization=require_organization(request)).values()[:100]))
