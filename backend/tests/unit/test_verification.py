from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.agents.verification.agent import VerificationAgent
from app.schemas import SourceEvidence, TaxpayerData


def test_verification_rejects_unsupported_critical_value():
    calculator = TaxCalculator()
    data = TaxpayerData(
        employee_name="Jordan Lee",
        employer_name="Example Corp",
        wages=Decimal("80000"),
        federal_tax_withheld=Decimal("10000"),
        field_confidence={"wages": 0.99},
        evidence=[
            SourceEvidence(
                field="wages", raw_text="80000", confidence=0.99
            )
        ],
    )
    result, _ = VerificationAgent(calculator, 0.95).run(
        data, calculator.calculate(data)
    )
    assert not result.valid
    assert "federal_tax_withheld" in result.hallucination_flags
