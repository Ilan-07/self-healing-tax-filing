"""Exercises the LangGraph self-healing loop with lightweight stub agents.

No OCR / Ollama / ReportLab needed -- this validates routing: the
verify -> remediate -> (re-extract | recalc) -> verify cycle and its bounded
escape to manual review.
"""

from pathlib import Path

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    AuditEntry,
    FilingReceipt,
    VerificationCheck,
    VerificationResult,
)
from app.synthetic import synthetic_return
from app.workflow.graph import TaxWorkflow


class StubReading:
    def __init__(self):
        self.calls = 0

    def run_many(self, paths, scale=2):
        self.calls += 1
        return synthetic_return(), "raw text", [
            AuditEntry(agent="reading", action="extract", reason="stub")
        ]


class StubProcessing:
    def run(self, data):
        return TaxCalculator().calculate(data), AuditEntry(
            agent="processing", action="calc", reason="stub"
        )


class StubVerifier:
    """Reports invalid for the first ``fail_times`` calls, then valid."""

    def __init__(self, fail_times: int, requires_reextraction: bool):
        self.calls = 0
        self.fail_times = fail_times
        self.requires_reextraction = requires_reextraction

    def run(self, data, calculation, transcript=None):
        self.calls += 1
        valid = self.calls > self.fail_times
        result = VerificationResult(
            valid=valid,
            confidence_score=0.99 if valid else 0.5,
            checks=[VerificationCheck(name="x", passed=valid, message="m")],
            requires_reextraction=not valid and self.requires_reextraction,
            correctness_ok=valid,
        )
        return result, AuditEntry(agent="verify", action="verify", reason="stub")


class StubRemediation:
    def run(self, data, verification):
        return (
            data,
            verification.requires_reextraction,
            AuditEntry(agent="remediate", action="fix", reason="stub"),
        )


class StubDocumentation:
    def run(self, result, output: Path, preview=None):
        receipt = FilingReceipt(
            submission_id=result.submission_id,
            reference_number="ACK123",
            timestamp=__import__("datetime").datetime.now(),
            filing_status="accepted",
        )
        return receipt, output, AuditEntry(
            agent="docs", action="generate", reason="stub"
        )


def _workflow(verifier, reading=None, max_attempts=2):
    return TaxWorkflow(
        reading=reading or StubReading(),
        processing=StubProcessing(),
        verification=verifier,
        remediation=StubRemediation(),
        documentation=StubDocumentation(),
        max_attempts=max_attempts,
    )


def _state(sub_id="sub-1"):
    return {
        "submission_id": sub_id,
        "original_filename": "w2.pdf",
        "upload_path": "/tmp/w2.pdf",
        "report_path": "/tmp/out.pdf",
        "status": "parsing",
        "audit_trail": [],
        "remediation_attempts": 0,
    }


def test_valid_return_completes_immediately():
    wf = _workflow(StubVerifier(fail_times=0, requires_reextraction=False))
    out = wf.run(_state())
    assert out["status"] == "completed"
    assert out["receipt"]["reference_number"] == "ACK123"


def test_remediation_then_success_recalculates_without_reextraction():
    reading = StubReading()
    wf = _workflow(
        StubVerifier(fail_times=1, requires_reextraction=False), reading=reading
    )
    out = wf.run(_state("sub-2"))
    assert out["status"] == "completed"
    assert reading.calls == 1  # recalc path, no re-extraction
    assert out["remediation_attempts"] == 1


def test_reextraction_loop_is_bounded_and_escapes_to_manual_review():
    reading = StubReading()
    wf = _workflow(
        StubVerifier(fail_times=99, requires_reextraction=True),
        reading=reading,
        max_attempts=2,
    )
    out = wf.run(_state("sub-3"))
    assert out["status"] == "manual_review"
    # initial parse + one re-extraction per remediation attempt (2) = 3.
    assert reading.calls == 3
