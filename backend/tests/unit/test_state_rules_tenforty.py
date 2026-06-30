"""Golden-case tests for the high-accuracy tenforty-backed state packs.

The expected values are produced by tenforty's OpenTaxSolver engine (the
authoritative oracle these packs delegate to) and pinned here so that a wiring
regression or a tenforty version bump that changes results is caught. California
is additionally validated by tenforty against professional tax software.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import FilingStatus, TaxpayerData
from app.state_rules import get_state_pack
from app.state_rules.base import FederalContext, FlatStatePack
from app.state_rules.tenforty_backend import TenfortyStatePack, evaluate_return


def _state_tax(**kwargs) -> Decimal:
    base: dict = dict(tax_year=2025, filing_status=FilingStatus.SINGLE)
    base.update(kwargs)
    return TaxCalculator().calculate(TaxpayerData(**base)).state_tax


# (state, scenario-kwargs) -> expected state tax, from tenforty 2025.
_SINGLE_80K = dict(wages=Decimal("80000"))
_MFJ_150K = dict(
    wages=Decimal("150000"),
    filing_status=FilingStatus.MARRIED_JOINTLY,
    qualifying_children=2,
)
_SINGLE_INVEST = dict(
    wages=Decimal("60000"),
    qualified_dividends=Decimal("5000"),
    ordinary_dividends=Decimal("5000"),
    long_term_capital_gain=Decimal("10000"),
)
# Retiree (65+): 30k wages + 25k taxable pension + 20k Social Security. SS is
# excluded by all four states; NY applies its $20k pension exclusion (pension
# 25k -> 5k taxed), CA taxes pension in full, NJ uses tenforty's own treatment.
_RETIREE = dict(
    age_65_plus=True,
    wages=Decimal("30000"),
    taxable_pension_ira=Decimal("25000"),
    social_security_benefits=Decimal("20000"),
)

GOLDEN = {
    ("CA", "single_80k"): (_SINGLE_80K, Decimal("3196")),
    ("CA", "mfj_150k_2dep"): (_MFJ_150K, Decimal("4599")),
    ("CA", "single_invest"): (_SINGLE_INVEST, Decimal("2775")),
    ("CA", "retiree"): (_RETIREE, Decimal("1340")),
    ("NY", "single_80k"): (_SINGLE_80K, Decimal("3797")),
    ("NY", "mfj_150k_2dep"): (_MFJ_150K, Decimal("7316")),
    ("NY", "single_invest"): (_SINGLE_INVEST, Decimal("3522")),
    ("NY", "retiree"): (_RETIREE, Decimal("1322")),
    ("NJ", "single_80k"): (_SINGLE_80K, Decimal("2904")),
    ("NJ", "mfj_150k_2dep"): (_MFJ_150K, Decimal("7365")),
    # 2595 (not the old 2042): NJ taxes capital gains as ordinary income, which
    # OTS-NJ silently dropped; our income routing restores it.
    ("NJ", "single_invest"): (_SINGLE_INVEST, Decimal("2595")),
    ("NJ", "retiree"): (_RETIREE, Decimal("437")),
    ("AZ", "single_80k"): (_SINGLE_80K, Decimal("1606")),
    ("AZ", "mfj_150k_2dep"): (_MFJ_150K, Decimal("2963")),
    ("AZ", "single_invest"): (_SINGLE_INVEST, Decimal("1481")),
    ("AZ", "retiree"): (_RETIREE, Decimal("981")),
}


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
@pytest.mark.parametrize("key", list(GOLDEN), ids=lambda k: f"{k[0]}_{k[1]}")
def test_tenforty_golden_cases(key):
    scenario, expected = GOLDEN[key]
    assert _state_tax(state=key[0], **scenario) == expected


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
@pytest.mark.parametrize("state", ["CA", "NY", "NJ", "AZ"])
def test_social_security_is_excluded(state):
    # All four states fully exclude Social Security from income tax.
    assert _state_tax(
        state=state, age_65_plus=True, social_security_benefits=Decimal("40000")
    ) == Decimal("0")


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_ny_pension_exclusion_applies_only_when_age_eligible():
    pension = dict(taxable_pension_ira=Decimal("25000"), wages=Decimal("30000"))
    young = _state_tax(state="NY", age_65_plus=False, **pension)
    senior = _state_tax(state="NY", age_65_plus=True, **pension)
    # The 65+ filer pays less: $20k of the pension is excluded for them.
    assert senior < young


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_nj_non_retirement_income_is_taxed_not_excluded():
    # Regression: OTS unconditionally excludes NJ Schedule-1 income, so a
    # non-retiree's partnership income must be routed to w2_income and taxed.
    wages_only = _state_tax(state="NJ", wages=Decimal("55000"))
    with_partnership = _state_tax(
        state="NJ", age=40, wages=Decimal("30000"),
        partnership_income=Decimal("25000"),
    )
    assert with_partnership == wages_only  # same $55k taxable base


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_nj_retirement_exclusion_age_and_income_limits():
    pension = dict(wages=Decimal("30000"), taxable_pension_ira=Decimal("25000"))
    young = _state_tax(state="NJ", age=50, **pension)
    senior = _state_tax(state="NJ", age=62, **pension)
    assert senior < young  # 62+ gets the exclusion at this income level
    # Above NJ's $150k gross-income ceiling the exclusion vanishes even at 62+.
    hi_young = _state_tax(
        state="NJ", age=50, wages=Decimal("160000"),
        taxable_pension_ira=Decimal("25000"),
    )
    hi_senior = _state_tax(
        state="NJ", age=62, wages=Decimal("160000"),
        taxable_pension_ira=Decimal("25000"),
    )
    assert hi_senior == hi_young


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_ny_pension_exclusion_covers_the_59_5_to_64_window():
    pension = dict(wages=Decimal("30000"), taxable_pension_ira=Decimal("25000"))
    young = _state_tax(state="NY", age=50, **pension)
    in_window = _state_tax(state="NY", age=62, **pension)  # 60-64, no 65+ flag
    assert in_window < young


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_nj_other_retirement_income_exclusion():
    # 62+, earned income <= $3,000, total under the cap: the Other Retirement
    # Income Exclusion extends to interest/dividends, so nothing is taxed.
    full_retiree = _state_tax(
        state="NJ", age=65, taxable_pension_ira=Decimal("10000"),
        taxable_interest=Decimal("5000"), ordinary_dividends=Decimal("5000"),
    )
    assert full_retiree == Decimal("0")
    # With >$3,000 earned income the ORIE does not apply, so the investment
    # income is taxed.
    with_earned = _state_tax(
        state="NJ", age=65, wages=Decimal("10000"),
        taxable_interest=Decimal("5000"), ordinary_dividends=Decimal("5000"),
    )
    assert with_earned > Decimal("0")


@pytest.mark.skipif(evaluate_return is None, reason="tenforty not installed")
def test_birth_date_drives_exact_ny_59_5_boundary():
    pension = dict(wages=Decimal("30000"), taxable_pension_ira=Decimal("25000"))
    # ~60 at 2025 year-end: past 59.5 -> exclusion applies.
    eligible = _state_tax(state="NY", birth_date=date(1966, 1, 1), **pension)
    # ~58.5 at year-end: under 59.5 -> no exclusion, despite being "59" in years.
    not_eligible = _state_tax(state="NY", birth_date=date(1967, 6, 1), **pension)
    assert eligible < not_eligible


def test_priority_states_use_verified_tenforty_packs():
    for state in ("CA", "NY", "NJ", "AZ"):
        pack = get_state_pack(state, 2025)
        assert isinstance(pack, TenfortyStatePack)
        assert pack.verified is True


def test_falls_back_to_reference_pack_on_engine_error():
    # year 2017 is outside tenforty's supported range -> engine raises -> the
    # reference fallback must run so the pipeline never fails.
    fallback = FlatStatePack(
        state="CA", year=2017, source="test", verified=False, rate=Decimal("0.05")
    )
    pack = TenfortyStatePack(
        state="CA", year=2017, source="test", verified=False, fallback=fallback
    )
    data = TaxpayerData(tax_year=2017, wages=Decimal("80000"), state="CA")
    federal = FederalContext(
        filing_status=FilingStatus.SINGLE,
        agi=Decimal("80000"),
        taxable_income=Decimal("64250"),
    )
    result = pack.compute(data, federal)
    assert result.tax == Decimal("3213")  # 64,250 * 5% via the fallback
    assert any("fell back to reference pack" in line for line in result.trace)
