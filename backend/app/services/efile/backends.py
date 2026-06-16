from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.schemas import SubmissionResult


@dataclass
class SubmissionAck:
    """A normalized acknowledgement, modelled on an IRS MeF acknowledgement."""

    accepted: bool
    channel: str  # "self_file" | "mef_transmitter"
    status: str  # human-readable status
    acknowledgement_id: str | None = None
    reject_codes: list[str] | None = None
    instructions: str | None = None


class EFileBackend(Protocol):
    def submit(self, result: SubmissionResult) -> SubmissionAck: ...


class PdfSelfFileBackend:
    """Default: hand the verified return back to the taxpayer to self-file."""

    channel = "self_file"

    def submit(self, result: SubmissionResult) -> SubmissionAck:
        return SubmissionAck(
            accepted=True,
            channel=self.channel,
            status="ready_to_self_file",
            instructions=(
                "Return is complete. File it yourself by mailing the printed "
                "Form 1040, or by entering these figures into IRS Free File "
                "Fillable Forms / IRS Direct File. No e-file credentials are "
                "used by this system."
            ),
        )


class MockTransmitterBackend:
    """Simulates a commercial MeF transmitter to demonstrate the adapter swap.

    Deterministic: only verified, balanced returns are 'Accepted'.
    """

    channel = "mef_transmitter"

    def submit(self, result: SubmissionResult) -> SubmissionAck:
        verified = bool(result.verification and result.verification.valid)
        if not verified:
            return SubmissionAck(
                accepted=False,
                channel=self.channel,
                status="rejected",
                reject_codes=["R0000-902"],  # mimics an MeF business-rule reject
            )
        seed = f"{result.submission_id}:{datetime.now(timezone.utc).date()}"
        ack_id = hashlib.sha256(seed.encode()).hexdigest()[:16].upper()
        return SubmissionAck(
            accepted=True,
            channel=self.channel,
            status="accepted",
            acknowledgement_id=ack_id,
        )


def get_backend(name: str) -> EFileBackend:
    backends: dict[str, EFileBackend] = {
        "pdf": PdfSelfFileBackend(),
        "mock_transmitter": MockTransmitterBackend(),
    }
    if name not in backends:
        raise ValueError(
            f"Unknown e-file backend '{name}' (available: {', '.join(backends)})"
        )
    return backends[name]
