from app.agents.verification.completeness import check_completeness
from app.schemas import (
    SubmissionResult,
    TaxpayerData,
    VerificationResult,
    WorkflowStatus,
)
from app.services.efile import MockTransmitterBackend, PdfSelfFileBackend, get_backend
from app.synthetic import synthetic_return, synthetic_transcript


def _result(valid: bool) -> SubmissionResult:
    return SubmissionResult(
        submission_id="abc12345-0000",
        status=WorkflowStatus.VERIFYING,
        original_filename="w2.pdf",
        extracted_data=synthetic_return(),
        verification=VerificationResult(
            valid=valid, confidence_score=0.99, checks=[]
        ),
    )


def test_completeness_ok_when_transcript_reconciles():
    data = synthetic_return()
    report = check_completeness(data, synthetic_transcript(data))
    assert report.ok
    assert report.issues == []


def test_completeness_heuristic_flags_no_income():
    report = check_completeness(TaxpayerData(employee_name="X"))
    assert not report.ok


def test_pdf_backend_always_ready_to_self_file():
    ack = PdfSelfFileBackend().submit(_result(valid=True))
    assert ack.accepted
    assert ack.channel == "self_file"
    assert ack.instructions


def test_mock_transmitter_accepts_valid_and_rejects_invalid():
    accepted = MockTransmitterBackend().submit(_result(valid=True))
    rejected = MockTransmitterBackend().submit(_result(valid=False))
    assert accepted.accepted and accepted.acknowledgement_id
    assert not rejected.accepted and rejected.reject_codes


def test_get_backend_resolves_names():
    assert isinstance(get_backend("pdf"), PdfSelfFileBackend)
    assert isinstance(get_backend("mock_transmitter"), MockTransmitterBackend)
