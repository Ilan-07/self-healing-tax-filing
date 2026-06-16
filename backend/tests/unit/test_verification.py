from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.agents.verification.agent import VerificationAgent
from app.schemas import SourceEvidence, TaxpayerData, W2
from app.synthetic import synthetic_return, synthetic_transcript


def _verify(data: TaxpayerData, transcript=None, threshold: float = 0.95):
    calculator = TaxCalculator()
    return VerificationAgent(calculator, threshold).run(
        data, calculator.calculate(data), transcript=transcript
    )


def test_verification_rejects_unsupported_critical_value():
    data = TaxpayerData(
        employee_name="Jordan Lee",
        ssn="123-45-6789",
        wages=Decimal("80000"),
        federal_tax_withheld=Decimal("10000"),
        field_confidence={"wages": 0.99},
        evidence=[SourceEvidence(field="wages", raw_text="80000", confidence=0.99)],
    )
    result, _ = _verify(data)
    assert not result.valid
    # Federal withholding is unsupported -> hallucination flag + re-extraction.
    assert "federal_tax_withheld" in result.hallucination_flags
    assert result.requires_reextraction is True


def test_synthetic_return_is_valid():
    data = synthetic_return()
    result, _ = _verify(data, transcript=synthetic_transcript(data))
    assert result.valid
    assert result.correctness_ok
    assert result.completeness_ok


def test_incomplete_w2_extraction_is_flagged():
    # A noisy scan that yields wages but no SS/Medicare boxes must not pass.
    data = TaxpayerData(
        employee_name="Pat Doe", ssn="123-45-6789", wages=Decimal("124132.08"),
        evidence=[SourceEvidence(field="wages", raw_text="124132.08", confidence=0.9)],
        field_confidence={"wages": 0.9},
    )
    result, _ = _verify(data)
    names = {c.name: c.passed for c in result.checks}
    assert names["w2_complete"] is False
    assert not result.valid


def test_w2_invariant_catches_bad_social_security_withholding():
    # box4 should be ~6.2% of box3; here it is wildly off.
    w2 = W2(
        box1_wages=Decimal("50000"),
        box2_federal_withheld=Decimal("5000"),
        box3_ss_wages=Decimal("50000"),
        box4_ss_withheld=Decimal("9000"),  # should be ~3,100
        box5_medicare_wages=Decimal("50000"),
        box6_medicare_withheld=Decimal("725"),
    )
    data = TaxpayerData(
        employee_name="Pat Doe", ssn="111-22-3333", w2s=[w2],
        evidence=[
            SourceEvidence(field="wages", raw_text="50000", confidence=0.99),
            SourceEvidence(field="federal_tax_withheld", raw_text="5000", confidence=0.99),
        ],
        field_confidence={"wages": 0.99, "federal_tax_withheld": 0.99},
    )
    data.aggregate_w2s()
    result, _ = _verify(data)
    names = {c.name: c.passed for c in result.checks}
    assert names["w2_social_security_invariant"] is False
    assert not result.correctness_ok


def test_completeness_flags_income_missing_vs_transcript():
    data = synthetic_return()
    transcript = synthetic_transcript(data)
    transcript["ordinary_dividends"] = "5000"  # IRS has a 1099-DIV we don't
    result, _ = _verify(data, transcript=transcript)
    assert result.completeness_ok is False
    assert not result.valid
