from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import FilingStatus, TaxpayerData


def test_single_filer_uses_2025_progressive_brackets():
    result = TaxCalculator().calculate(
        TaxpayerData(
            employee_name="Jordan Lee",
            employer_name="Example Corp",
            filing_status=FilingStatus.SINGLE,
            tax_year=2025,
            wages=Decimal("80000"),
            federal_tax_withheld=Decimal("12000"),
            state_tax_withheld=Decimal("3000"),
            state_tax_rate=Decimal("0.05"),
        )
    )

    assert result.taxable_income == Decimal("65000.00")
    assert result.federal_tax == Decimal("9214.00")
    assert result.state_tax == Decimal("3250.00")
    assert result.refund == Decimal("2536.00")
    assert result.tax_due == Decimal("0")


def test_itemized_deduction_wins_when_larger():
    result = TaxCalculator().calculate(
        TaxpayerData(
            wages=Decimal("50000"),
            itemized_deductions=Decimal("20000"),
        )
    )
    assert result.deductions == Decimal("20000.00")
    assert result.taxable_income == Decimal("30000.00")
