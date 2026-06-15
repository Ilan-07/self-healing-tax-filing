from datetime import datetime, timezone
from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    AuditEntry,
    FilingReceipt,
    SourceEvidence,
    SubmissionResult,
    TaxpayerData,
    VerificationCheck,
    VerificationResult,
)
from app.services.pdf.report import PDFReportService


def test_pdf_contains_complete_report(tmp_path):
    data = TaxpayerData(
        employee_name="Jordan Lee",
        employer_name="Example Corp",
        wages=Decimal("80000"),
        federal_tax_withheld=Decimal("12000"),
        state_tax_withheld=Decimal("3000"),
        evidence=[
            SourceEvidence(field="wages", raw_text="80000", confidence=0.99),
            SourceEvidence(
                field="federal_tax_withheld",
                raw_text="12000",
                confidence=0.99,
            ),
        ],
    )
    calculation = TaxCalculator().calculate(data)
    verification = VerificationResult(
        valid=True,
        confidence_score=0.99,
        checks=[
            VerificationCheck(
                name="calculation_replay",
                passed=True,
                message="Independent calculation matched",
            )
        ],
    )
    result = SubmissionResult(
        submission_id="12345678-1234-1234-1234-123456789012",
        status="completed",
        original_filename="w2.pdf",
        extracted_data=data,
        calculation=calculation,
        verification=verification,
        audit_trail=[
            AuditEntry(
                agent="Verification Agent",
                action="verify",
                reason="All checks passed",
            )
        ],
    )
    receipt = FilingReceipt(
        submission_id=result.submission_id,
        reference_number="TX2025-12345678",
        timestamp=datetime.now(timezone.utc),
        filing_status="ready_for_filing",
    )
    output = tmp_path / "report.pdf"

    PDFReportService().generate(result, receipt, output)

    assert output.exists()
    assert output.stat().st_size > 2000
