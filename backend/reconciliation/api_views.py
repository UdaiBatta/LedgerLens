from django.db.models import Count, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import InvestigationAgent
from .models import AgentRun, EvidenceConnection, FinancialRecord, FinancialRecordType, ReconciliationCase, ReconciliationStatus
from .serializers import (
    AgentRunSerializer,
    AuditLogEntrySerializer,
    FinancialRecordSerializer,
    ReconciliationCaseDetailSerializer,
    ReconciliationCaseListSerializer,
)


class ReconciliationCaseViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"

    def get_queryset(self):
        queryset = ReconciliationCase.objects.select_related(
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
    queryset = FinancialRecord.objects.select_related("source", "source__organization")
    serializer_class = FinancialRecordSerializer


class OverviewMetricsView(APIView):
    def get(self, request):
        captured = FinancialRecord.objects.filter(
            record_type=FinancialRecordType.PAYMENT
        ).aggregate(total=Sum("amount_minor"))["total"] or 0
        case_counts = ReconciliationCase.objects.aggregate(
            total=Count("id"),
            matched=Count("id", filter=Q(status=ReconciliationStatus.MATCHED)),
            open=Count("id", filter=~Q(status=ReconciliationStatus.MATCHED)),
        )
        unexplained = sum(
            abs(reconciliation_case.difference_minor)
            for reconciliation_case in ReconciliationCase.objects.exclude(
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
            summary = FinancialRecord.objects.filter(record_type=record_type).aggregate(
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
            for agent_run in AgentRun.objects.select_related("reconciliation_case")
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
            for evidence_connection in EvidenceConnection.objects.select_related(
                "reconciliation_case", "source_record", "destination_record"
            )
        ]
        entries = sorted(
            agent_run_entries + evidence_connection_entries,
            key=lambda entry: entry["occurred_at"],
            reverse=True,
        )
        return Response(AuditLogEntrySerializer(entries, many=True).data)
