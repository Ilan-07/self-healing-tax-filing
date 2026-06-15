from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.documentation.agent import DocumentationAgent
from app.agents.reading.agent import ReadingAgent
from app.agents.remediation.agent import RemediationAgent
from app.agents.tax_processing.agent import TaxProcessingAgent
from app.agents.verification.agent import VerificationAgent
from app.schemas import SubmissionResult, TaxCalculation, TaxpayerData, VerificationResult
from app.workflow.state import TaxWorkflowState


class TaxWorkflow:
    def __init__(
        self,
        reading: ReadingAgent,
        processing: TaxProcessingAgent,
        verification: VerificationAgent,
        remediation: RemediationAgent,
        documentation: DocumentationAgent,
        max_attempts: int,
    ):
        self.reading = reading
        self.processing = processing
        self.verifier = verification
        self.remediation = remediation
        self.documentation = documentation
        self.max_attempts = max_attempts
        self.graph = self._build()

    def _build(self):
        graph = StateGraph(TaxWorkflowState)
        graph.add_node("parse", self._parse)
        graph.add_node("calculate", self._calculate)
        graph.add_node("verify", self._verify)
        graph.add_node("remediate", self._remediate)
        graph.add_node("document", self._document)
        graph.add_node("manual_review", self._manual_review)
        graph.add_edge(START, "parse")
        graph.add_edge("parse", "calculate")
        graph.add_edge("calculate", "verify")
        graph.add_conditional_edges(
            "verify",
            self._route_verification,
            {
                "document": "document",
                "remediate": "remediate",
                "manual_review": "manual_review",
            },
        )
        graph.add_edge("remediate", "calculate")
        graph.add_edge("document", END)
        graph.add_edge("manual_review", END)
        return graph.compile()

    def run(self, state: TaxWorkflowState) -> TaxWorkflowState:
        try:
            return self.graph.invoke(state)
        except Exception as exc:
            return {**state, "status": "failed", "error": str(exc)}

    def _parse(self, state):
        data, raw_text, logs = self.reading.run(
            __import__("pathlib").Path(state["upload_path"])
        )
        return {
            "status": "calculating",
            "extracted_data": data.model_dump(mode="json"),
            "raw_text": raw_text,
            "audit_trail": state.get("audit_trail", [])
            + [item.model_dump(mode="json") for item in logs],
        }

    def _calculate(self, state):
        calculation, log = self.processing.run(
            TaxpayerData.model_validate(state["extracted_data"])
        )
        return {
            "status": "verifying",
            "calculation": calculation.model_dump(mode="json"),
            "audit_trail": state.get("audit_trail", [])
            + [log.model_dump(mode="json")],
        }

    def _verify(self, state):
        result, log = self.verifier.run(
            TaxpayerData.model_validate(state["extracted_data"]),
            TaxCalculation.model_validate(state["calculation"]),
        )
        return {
            "verification": result.model_dump(mode="json"),
            "audit_trail": state.get("audit_trail", [])
            + [log.model_dump(mode="json")],
        }

    def _route_verification(self, state):
        result = VerificationResult.model_validate(state["verification"])
        if result.valid:
            return "document"
        if state.get("remediation_attempts", 0) < self.max_attempts:
            return "remediate"
        return "manual_review"

    def _remediate(self, state):
        data, log = self.remediation.run(
            TaxpayerData.model_validate(state["extracted_data"]),
            VerificationResult.model_validate(state["verification"]),
        )
        return {
            "status": "remediating",
            "extracted_data": data.model_dump(mode="json"),
            "remediation_attempts": state.get("remediation_attempts", 0) + 1,
            "audit_trail": state.get("audit_trail", [])
            + [log.model_dump(mode="json")],
        }

    def _document(self, state):
        result = SubmissionResult.model_validate(
            {
                "submission_id": state["submission_id"],
                "status": "completed",
                "original_filename": state["original_filename"],
                "extracted_data": state["extracted_data"],
                "calculation": state["calculation"],
                "verification": state["verification"],
                "audit_trail": state.get("audit_trail", []),
            }
        )
        receipt, path, log = self.documentation.run(
            result,
            __import__("pathlib").Path(state["report_path"]),
            __import__("pathlib").Path(state["upload_path"]),
        )
        return {
            "status": "completed",
            "receipt": receipt.model_dump(mode="json"),
            "audit_trail": state.get("audit_trail", [])
            + [log.model_dump(mode="json")],
        }

    @staticmethod
    def _manual_review(state):
        return {"status": "manual_review"}
