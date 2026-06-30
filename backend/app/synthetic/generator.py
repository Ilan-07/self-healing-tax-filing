"""Build fully-grounded synthetic returns and matching IRS-style transcripts."""

from __future__ import annotations

from decimal import Decimal

from app.schemas import FilingStatus, SourceEvidence, TaxpayerData, W2


def _w2(
    *,
    employer: str,
    ein: str,
    wages: Decimal,
    federal: Decimal,
    state: Decimal = Decimal("0"),
    state_code: str = "",
) -> W2:
    """A W-2 with statutorily-consistent Social Security / Medicare boxes."""
    return W2(
        employer_name=employer,
        employer_ein=ein,
        box1_wages=wages,
        box2_federal_withheld=federal,
        box3_ss_wages=wages,
        box4_ss_withheld=(wages * Decimal("0.062")).quantize(Decimal("0.01")),
        box5_medicare_wages=wages,
        box6_medicare_withheld=(wages * Decimal("0.0145")).quantize(
            Decimal("0.01")
        ),
        box15_state=state_code,
        box17_state_withheld=state,
    )


def synthetic_return(
    *,
    filing_status: FilingStatus = FilingStatus.SINGLE,
    qualifying_children: int = 0,
    tax_year: int = 2025,
) -> TaxpayerData:
    """A realistic, fully source-grounded W-2 return that should verify VALID."""
    w2 = _w2(
        employer="Globex Corporation",
        ein="12-3456789",
        wages=Decimal("85000"),
        federal=Decimal("11000"),
        state=Decimal("3500"),
        state_code="CA",
    )
    data = TaxpayerData(
        employee_name="Jordan Q. Sample",
        ssn="123-45-6789",
        filing_status=filing_status,
        tax_year=tax_year,
        qualifying_children=qualifying_children,
        w2s=[w2],
        taxable_interest=Decimal("420"),
        evidence=[
            SourceEvidence(field="wages", raw_text="85000", confidence=0.99),
            SourceEvidence(
                field="federal_tax_withheld", raw_text="11000", confidence=0.99
            ),
            SourceEvidence(
                field="state_tax_withheld", raw_text="3500", confidence=0.98
            ),
            SourceEvidence(
                field="taxable_interest", raw_text="420", confidence=0.97
            ),
            SourceEvidence(field="ssn", raw_text="***-**-6789", confidence=0.95),
        ],
        field_confidence={
            "wages": 0.99,
            "federal_tax_withheld": 0.99,
            "state_tax_withheld": 0.98,
            "taxable_interest": 0.97,
            "ssn": 0.95,
        },
    )
    data.aggregate_w2s()  # folds the W-2 boxes into wage/withholding totals
    return data


def synthetic_transcript(data: TaxpayerData) -> dict[str, object]:
    """The IRS Wage & Income transcript the taxpayer's docs should reconcile to."""
    return {
        "wages": str(data.wages),
        "taxable_interest": str(data.taxable_interest),
        "ordinary_dividends": str(data.ordinary_dividends),
        "self_employment_income": str(data.self_employment_income),
        "long_term_capital_gain": str(data.long_term_capital_gain),
    }
