from app.schemas import AuditEntry, TaxpayerData, VerificationResult
from app.services.ollama.client import OllamaClient


class RemediationAgent:
    name = "Remediation Agent"

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def run(
        self, data: TaxpayerData, verification: VerificationResult
    ) -> tuple[TaxpayerData, AuditEntry]:
        updated = data.model_copy(deep=True)
        changes: dict[str, str] = {}
        classification = self.ollama.classify_remediation(
            verification.errors
        )

        for field in verification.hallucination_flags:
            setattr(updated, field, 0)
            changes[field] = "Removed unsupported value"

        for field, value in list(updated.field_confidence.items()):
            normalized = min(max(float(value), 0), 1)
            if normalized != value:
                updated.field_confidence[field] = normalized
                changes[field] = "Normalized confidence to [0, 1]"

        return updated, AuditEntry(
            agent=self.name,
            action="remediate",
            reason="Correct deterministic and source-grounding failures",
            details={
                "root_causes": verification.errors,
                "local_model_classification": classification,
                "changes": changes,
                "requires_reextraction": not bool(changes),
            },
        )
