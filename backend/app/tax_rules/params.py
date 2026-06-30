"""Versioned federal tax parameters.

Every numeric constant the engine relies on lives in a ``TaxYearParams`` value
that carries its own provenance (``source`` + ``verified``).  Constants must
never be invented by the LLM and must be traceable to an IRS publication so a
reviewer can confirm they are current.

``verified=False`` means "transcribed from the cited source but not yet
double-checked against the published PDF in this environment" -- treat those
returns as advisory until a maintainer flips the flag after verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.schemas import FilingStatus


Bracket = tuple[Decimal | None, Decimal]


def progressive_tax(amount: Decimal, brackets: list[Bracket]) -> Decimal:
    """Exact progressive tax on ``amount`` over ascending ``(upper, rate)`` bands.

    The final band must be open (``upper is None``). Shared by the federal
    engine and by state rule packs so the bracket math lives in one place.
    """
    tax = Decimal("0")
    lower = Decimal("0")
    for upper, rate in brackets:
        if amount <= lower:
            break
        band_top = amount if upper is None else min(amount, upper)
        tax += (band_top - lower) * rate
        if upper is None or amount <= upper:
            break
        lower = upper
    return tax


@dataclass(frozen=True)
class CreditParams:
    """Child Tax Credit / Credit for Other Dependents parameters."""

    ctc_per_child: Decimal
    ctc_refundable_cap: Decimal  # max refundable (Additional CTC) per child
    odc_per_dependent: Decimal
    phaseout_start: dict[FilingStatus, Decimal]
    phaseout_per_1000: Decimal  # credit reduction per $1,000 over the threshold


@dataclass(frozen=True)
class EitcTier:
    """Earned Income Tax Credit parameters for a given number of children."""

    credit_rate: Decimal
    earned_income_amount: Decimal  # income at which the credit plateaus
    max_credit: Decimal
    phaseout_begin_other: Decimal  # single / HoH / QSS
    phaseout_begin_mfj: Decimal
    phaseout_rate: Decimal


@dataclass(frozen=True)
class EitcParams:
    investment_income_limit: Decimal
    # Keyed by number of qualifying children: 0, 1, 2, 3 (3 = "3 or more").
    tiers: dict[int, EitcTier]


@dataclass(frozen=True)
class AmtParams:
    """Alternative Minimum Tax (Form 6251)."""

    exemption: dict[FilingStatus, Decimal]
    phaseout_start: dict[FilingStatus, Decimal]  # exemption phases out at 25%
    rate_28_threshold: Decimal  # AMTI over this is taxed at 28% (half for MFS)


@dataclass(frozen=True)
class EducationCreditParams:
    """American Opportunity Credit and Lifetime Learning Credit."""

    aotc_max_per_student: Decimal  # 2,500
    aotc_refundable_rate: Decimal  # 0.40
    llc_rate: Decimal  # 0.20
    llc_expense_cap: Decimal  # 10,000
    # MAGI phase-out (start, end) by filing status; absent = ineligible (MFS).
    phaseout: dict[FilingStatus, tuple[Decimal, Decimal]]


@dataclass(frozen=True)
class SaversCreditParams:
    """Retirement Savings Contributions Credit (Form 8880)."""

    contribution_cap: Decimal  # 2,000 per person
    # Ordered (agi_ceiling, rate) tiers by filing status; first match wins.
    tiers: dict[FilingStatus, list[tuple[Decimal, Decimal]]]


@dataclass(frozen=True)
class PreferentialRates:
    """0/15/20% break-points for qualified dividends and net LTCG.

    Values are the upper bound of *taxable income* for the 0% and 15% bands.
    """

    zero_rate_max: dict[FilingStatus, Decimal]
    fifteen_rate_max: dict[FilingStatus, Decimal]


@dataclass(frozen=True)
class TaxYearParams:
    year: int
    source: str
    verified: bool
    standard_deductions: dict[FilingStatus, Decimal]
    # Additional standard deduction per "box" for age 65+ or blindness.
    additional_std_married: Decimal
    additional_std_unmarried: Decimal
    brackets: dict[FilingStatus, list[Bracket]]
    preferential: PreferentialRates
    credits: CreditParams
    ss_wage_base: Decimal
    ss_rate: Decimal
    medicare_rate: Decimal
    addl_medicare_rate: Decimal
    addl_medicare_threshold: dict[FilingStatus, Decimal]
    niit_rate: Decimal
    niit_threshold: dict[FilingStatus, Decimal]
    se_net_factor: Decimal  # 0.9235 (1 - 7.65%)
    se_combined_rate: Decimal  # 0.153 (12.4% OASDI + 2.9% Medicare)
    qbi_rate: Decimal  # 0.20 Qualified Business Income deduction rate
    eitc: EitcParams | None = None
    amt: AmtParams | None = None
    education: EducationCreditParams | None = None
    savers: SaversCreditParams | None = None
    # OBBBA senior bonus deduction (2025-2028); None if not in effect.
    senior_deduction: Decimal | None = None
    senior_deduction_phaseout_start: dict[FilingStatus, Decimal] | None = None
    senior_deduction_phaseout_rate: Decimal | None = None


_REGISTRY: dict[int, TaxYearParams] = {}


def register(params: TaxYearParams) -> TaxYearParams:
    _REGISTRY[params.year] = params
    return params


def get_params(year: int) -> TaxYearParams:
    if year not in _REGISTRY:
        installed = ", ".join(str(y) for y in sorted(_REGISTRY)) or "none"
        raise ValueError(
            f"No federal tax parameters installed for {year} "
            f"(installed years: {installed})."
        )
    return _REGISTRY[year]
