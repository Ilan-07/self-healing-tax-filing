from datetime import datetime, timezone
from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    FilingReceipt,
    SubmissionResult,
    TaxpayerData,
    VerificationResult,
    WorkflowStatus,
)
from app.services.pdf.professional_report import ProfessionalReportService, _money


def _result(data: TaxpayerData) -> SubmissionResult:
    calc = TaxCalculator().calculate(data)
    return SubmissionResult(
        submission_id="rep-1",
        status=WorkflowStatus.COMPLETED,
        original_filename="w2.pdf",
        extracted_data=data,
        calculation=calc,
        verification=VerificationResult(valid=True, confidence_score=0.99, checks=[]),
    )


def _receipt(status="accepted") -> FilingReceipt:
    return FilingReceipt(
        submission_id="rep-1",
        reference_number="ACK-123",
        timestamp=datetime.now(timezone.utc),
        filing_status=status,
    )


def test_money_formatting():
    assert _money(Decimal("65000")) == "$65,000.00"
    assert _money(Decimal("-1150")) == "($1,150.00)"
    assert _money(None) == "$0.00"


def test_generates_report_for_refund_and_balance_due(tmp_path):
    refund_case = _result(
        TaxpayerData(employee_name="A B", ssn="123-45-6789", wages=Decimal("60000"),
                     federal_tax_withheld=Decimal("9000"))
    )
    due_case = _result(
        TaxpayerData(employee_name="C D", ssn="123-45-6789", wages=Decimal("200000"),
                     federal_tax_withheld=Decimal("1000"))
    )
    for name, res in (("refund.pdf", refund_case), ("due.pdf", due_case)):
        out = ProfessionalReportService().generate(res, _receipt(), tmp_path / name)
        blob = out.read_bytes()
        assert blob.startswith(b"%PDF-")
        assert len(blob) > 4000
