"""Remediation agent.

Performs *bounded, meaningful* corrections rather than blindly zeroing fields:

  * When a critical field (wages / federal withholding) is ungrounded, it does
    NOT invent or delete data -- it requests a re-extraction pass (the graph
    routes back to the reading agent with a higher-resolution render).
  * Non-critical ungrounded monetary fields are treated as likely
    hallucinations and removed.
  * Deterministic consistency fixes are applied (e.g. qualified dividends cannot
    exceed ordinary dividends; confidences clamped to [0, 1]).

The local coder model is used only to *classify* the failure, never to compute
or propose tax values.
"""

from __future__ import annotations

from decimal import Decimal

from app.schemas import AuditEntry, TaxpayerData, VerificationResult
from app.services.ollama.client import OllamaClient


CRITICAL_FIELDS = {"wages", "federal_tax_withheld"}


class RemediationAgent:
    name = "Remediation Agent"

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def run(
        self, data: TaxpayerData, verification: VerificationResult
    ) -> tuple[TaxpayerData, bool, AuditEntry]:
        updated = data.model_copy(deep=True)
        changes: dict[str, str] = {}
        classification = self.ollama.classify_remediation(verification.errors)

        needs_reextraction = verification.requires_reextraction

        # Drop only non-critical ungrounded fields; never fabricate/delete
        # critical income -- that triggers a re-extraction instead.
        for field in verification.hallucination_flags:
            if field in CRITICAL_FIELDS:
                continue
            if getattr(updated, field, None) not in (None, Decimal("0")):
                setattr(updated, field, Decimal("0"))
                changes[field] = "Removed unsupported (likely hallucinated) value"

        # Deterministic consistency repair.
        if updated.qualified_dividends > updated.ordinary_dividends:
            updated.qualified_dividends = updated.ordinary_dividends
            changes["qualified_dividends"] = "Capped at ordinary dividends"

        # Normalize confidences into range.
        for field, value in list(updated.field_confidence.items()):
            normalized = min(max(float(value), 0), 1)
            if normalized != value:
                updated.field_confidence[field] = normalized
                changes[field] = "Normalized confidence to [0, 1]"

        return updated, needs_reextraction, AuditEntry(
            agent=self.name,
            action="remediate",
            reason="Apply bounded corrections; re-extract when grounding fails",
            details={
                "root_causes": verification.errors,
                "local_model_classification": classification,
                "changes": changes,
                "requires_reextraction": needs_reextraction,
            },
        )
