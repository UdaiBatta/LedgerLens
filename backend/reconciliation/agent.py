import json
import os
from decimal import Decimal

from .models import AgentRun, FinancialRecord, ReconciliationCase


class InvestigationAgent:
    model_name = os.environ.get("ANTHROPIC_MODEL", "")

    def answer(self, reconciliation_case: ReconciliationCase, question: str) -> AgentRun:
        if not os.environ.get("ANTHROPIC_API_KEY") or not self.model_name:
            return self._deterministic_fallback(reconciliation_case, question)

        try:
            return self._run_anthropic_loop(reconciliation_case, question)
        except Exception:
            return self._deterministic_fallback(reconciliation_case, question)

    def _run_anthropic_loop(self, reconciliation_case, question):
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        messages = [{"role": "user", "content": question}]
        logged_tool_calls = []

        for _ in range(4):
            response = client.messages.create(
                model=self.model_name,
                max_tokens=900,
                system=(
                    "You investigate a financial reconciliation case. Use tools before concluding. "
                    "Never calculate or invent money values. Cite only record IDs returned by tools. "
                    "Return JSON with conclusion, confidence, recommended_action, evidence_cited, "
                    "and sufficient_evidence."
                ),
                tools=self._tool_definitions(),
                messages=messages,
            )
            tool_uses = [block for block in response.content if block.type == "tool_use"]
            if not tool_uses:
                response_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                result = self._parse_result(response_text)
                self._validate_citations(result, logged_tool_calls)
                return self._save_run(
                    reconciliation_case,
                    question,
                    logged_tool_calls,
                    result,
                    self.model_name,
                )

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tool_use in tool_uses:
                tool_result = self._execute_tool(reconciliation_case, tool_use.name, tool_use.input)
                logged_tool_calls.append(
                    {"name": tool_use.name, "input": tool_use.input, "result": tool_result}
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(tool_result),
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("The investigation exceeded the four-turn safety limit.")

    def _execute_tool(self, reconciliation_case, tool_name, tool_input):
        if tool_name == "get_check_results":
            return [
                {
                    "name": check.check_name,
                    "result": check.result,
                    "evidence": check.evidence,
                    "details": check.details,
                }
                for check in reconciliation_case.check_results.all()
            ]

        record_id = tool_input.get("record_id") or tool_input.get("reference")
        record = FinancialRecord.objects.filter(
            source__organization=reconciliation_case.organization,
            external_record_id=record_id,
        ).first()
        if not record:
            return {"found": False, "reference": record_id}
        return {
            "found": True,
            "record_id": record.external_record_id,
            "record_type": record.record_type,
            "amount_minor": record.amount_minor,
            "currency": record.currency,
            "occurred_at": record.occurred_at.isoformat(),
            "status": record.status,
        }

    def _deterministic_fallback(self, reconciliation_case, question):
        checks = list(reconciliation_case.check_results.all())
        cited = list(
            dict.fromkeys(reference for check in checks for reference in check.evidence)
        )
        insufficient = reconciliation_case.status == "insufficient_evidence"
        difference = Decimal(abs(reconciliation_case.difference_minor)) / Decimal("100")
        conclusion = (
            f"The first unsupported difference is {reconciliation_case.currency} "
            f"{difference:.2f} at "
            f"{reconciliation_case.exception_type.replace('_', ' ')}."
        )
        if insufficient:
            conclusion += " Existing records do not prove the underlying cause."
        return self._save_run(
            reconciliation_case,
            question,
            [{"name": "get_check_results", "input": {"case_id": str(reconciliation_case.public_id)}}],
            {
                "conclusion": conclusion,
                "confidence": 0.92,
                "recommended_action": (
                    "Request the missing source evidence and rerun reconciliation."
                    if insufficient
                    else "Review the failed deterministic check and its cited records."
                ),
                "evidence_cited": cited,
                "sufficient_evidence": not insufficient,
            },
            "deterministic-fallback",
        )

    def _save_run(self, reconciliation_case, question, tool_calls, result, model_version):
        return AgentRun.objects.create(
            reconciliation_case=reconciliation_case,
            question=question,
            tool_calls=tool_calls,
            conclusion=result["conclusion"],
            recommended_action=result.get("recommended_action", ""),
            confidence=Decimal(str(result.get("confidence", 0))),
            evidence_cited=result.get("evidence_cited", []),
            sufficient_evidence=bool(result.get("sufficient_evidence")),
            model_version=model_version,
        )

    @staticmethod
    def _parse_result(response_text):
        cleaned = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(cleaned)
        required = {"conclusion", "confidence", "evidence_cited", "sufficient_evidence"}
        if not required.issubset(result):
            raise ValueError("The model response did not match the investigation schema.")
        if not isinstance(result["conclusion"], str) or not result["conclusion"].strip():
            raise ValueError("The model conclusion must be non-empty text.")
        if not isinstance(result["evidence_cited"], list) or not all(
            isinstance(reference, str) for reference in result["evidence_cited"]
        ):
            raise ValueError("Evidence citations must be a list of record identifiers.")
        if not isinstance(result["sufficient_evidence"], bool):
            raise ValueError("The sufficient_evidence field must be boolean.")
        confidence = Decimal(str(result["confidence"]))
        if confidence < 0 or confidence > 1:
            raise ValueError("Confidence must be between zero and one.")
        return result

    @staticmethod
    def _validate_citations(result, tool_calls):
        allowed_references = set()
        for call in tool_calls:
            tool_result = call.get("result")
            if isinstance(tool_result, list):
                for check in tool_result:
                    allowed_references.update(check.get("evidence", []))
            elif isinstance(tool_result, dict) and tool_result.get("found"):
                allowed_references.add(tool_result["record_id"])
        unsupported = set(result["evidence_cited"]) - allowed_references
        if unsupported:
            raise ValueError("The model cited records that were not returned by its tools.")

    @staticmethod
    def _tool_definitions():
        record_tool = {
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
        }
        return [
            {
                "name": "get_transaction",
                "description": "Get a normalized financial record by its external identifier.",
                "input_schema": record_tool,
            },
            {
                "name": "get_bank_statement_line",
                "description": "Get a bank credit record by its transaction reference.",
                "input_schema": record_tool,
            },
            {
                "name": "get_settlement_report",
                "description": "Get a settlement record by its settlement identifier.",
                "input_schema": record_tool,
            },
            {
                "name": "get_check_results",
                "description": "Get deterministic check results for the active case.",
                "input_schema": {
                    "type": "object",
                    "properties": {"case_id": {"type": "string"}},
                    "required": ["case_id"],
                },
            },
        ]
