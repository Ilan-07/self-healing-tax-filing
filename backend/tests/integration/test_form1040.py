from datetime import datetime, timezone
from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    FilingReceipt,
    FilingStatus,
    SubmissionResult,
    TaxpayerData,
    VerificationResult,
    WorkflowStatus,
)
from app.services.pdf.form1040 import Form1040Service, money


def _result(data: TaxpayerData) -> SubmissionResult:
    calc = TaxCalculator().calculate(data)
    return SubmissionResult(
        submission_id="abc12345",
        status=WorkflowStatus.COMPLETED,
        original_filename="w2.pdf",
        extracted_data=data,
        calculation=calc,
        verification=VerificationResult(valid=True, confidence_score=0.99, checks=[]),
    )


def _receipt() -> FilingReceipt:
    return FilingReceipt(
        submission_id="abc12345",
        reference_number="ACK123",
        timestamp=datetime.now(timezone.utc),
        filing_status="accepted",
    )


def test_money_formatting():
    assert money(Decimal("12000")) == "12,000"
    assert money(Decimal("-3000")) == "(3,000)"
    assert money(None) == ""


def test_generates_valid_pdf_for_simple_and_complex_returns(tmp_path):
    simple = _result(TaxpayerData(employee_name="A", ssn="123-45-6789", wages=Decimal("80000")))
    complex_ = _result(
        TaxpayerData(
            employee_name="B",
            ssn="123-45-6789",
            filing_status=FilingStatus.MARRIED_JOINTLY,
            wages=Decimal("120000"),
            self_employment_income=Decimal("20000"),
            long_term_capital_gain=Decimal("15000"),
            qualifying_children=2,
            salt_paid=Decimal("18000"),
            mortgage_interest=Decimal("20000"),
        )
    )
    for name, result in (("s.pdf", simple), ("c.pdf", complex_)):
        out = Form1040Service().generate(result, _receipt(), tmp_path / name)
        blob = out.read_bytes()
        assert blob.startswith(b"%PDF-")
        assert len(blob) > 3000


def test_schedules_are_conditional():
    svc = Form1040Service()
    wage_only = TaxpayerData(wages=Decimal("80000"))
    wage_calc = TaxCalculator().calculate(wage_only)
    assert svc._schedule_se(wage_only, wage_calc) == []
    assert svc._form_8995(wage_calc) == []

    se = TaxpayerData(self_employment_income=Decimal("50000"))
    se_calc = TaxCalculator().calculate(se)
    assert svc._schedule_se(se, se_calc)  # non-empty
    assert svc._form_8995(se_calc)  # QBI present

    itemizer = TaxpayerData(
        filing_status=FilingStatus.SINGLE,
        wages=Decimal("150000"),
        salt_paid=Decimal("12000"),
        mortgage_interest=Decimal("15000"),
    )
    assert svc._schedule_a(itemizer, TaxCalculator().calculate(itemizer))
    assert svc._schedule_a(wage_only, wage_calc) == []  # standard deduction
