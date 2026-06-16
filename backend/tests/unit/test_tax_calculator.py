from decimal import Decimal

import pytest

from app.agents.tax_processing.tax_calculator import (
    TaxCalculator,
    dollars,
    tax_liability,
)
from app.schemas import FilingStatus, TaxCalculation, TaxpayerData
from app.tax_rules.params import get_params


def calc(**kwargs) -> TaxCalculation:
    defaults: dict = dict(tax_year=2025, filing_status=FilingStatus.SINGLE)
    defaults.update(kwargs)
    return TaxCalculator().calculate(TaxpayerData(**defaults))


def test_single_filer_uses_2025_standard_deduction_and_tax_table():
    r = calc(
        wages=Decimal("80000"),
        federal_tax_withheld=Decimal("12000"),
        state_tax_withheld=Decimal("3000"),
        state_tax_rate=Decimal("0.05"),
    )
    # 2025 standard deduction is 15,750 (OBBBA), not 15,000.
    assert r.standard_deduction == Decimal("15750")
    assert r.taxable_income == Decimal("64250")
    # Tax computed from the IRS Tax Table (midpoint of the $50 band), not the
    # raw marginal formula.
    assert r.tax_table_used is True
    assert r.income_tax_before_credits == Decimal("9055")
    assert r.federal_tax == Decimal("9055")
    assert r.state_tax == Decimal("3213")
    # Federal refund is federal-only (withholding 12,000 - tax 9,055).
    assert r.refund == Decimal("2945")
    assert r.tax_due == Decimal("0")
    # State is reported separately (state tax 3,213 - state withholding 3,000).
    assert r.state_balance_due == Decimal("213")


def test_tax_table_vs_worksheet_boundary_at_100k():
    params = get_params(2025)
    fs = FilingStatus.SINGLE
    below = tax_liability(Decimal("99950"), params, fs)  # Tax Table
    at = tax_liability(Decimal("100000"), params, fs)  # Tax Computation Worksheet
    assert below == Decimal("16909")
    assert at == Decimal("16914")


def test_itemized_deduction_wins_when_larger():
    r = calc(wages=Decimal("50000"), itemized_deductions=Decimal("20000"))
    assert r.deductions == Decimal("20000")
    assert r.taxable_income == Decimal("30000")


def test_mfj_with_two_children_gets_child_tax_credit():
    r = calc(
        filing_status=FilingStatus.MARRIED_JOINTLY,
        wages=Decimal("120000"),
        federal_tax_withheld=Decimal("10000"),
        qualifying_children=2,
    )
    assert r.taxable_income == Decimal("88500")
    assert r.income_tax_before_credits == Decimal("10146")
    assert r.child_tax_credit == Decimal("4400")  # 2 x $2,200
    assert r.federal_tax == Decimal("5746")
    assert r.refund == Decimal("4254")


def test_ctc_phases_out_above_threshold():
    r = calc(wages=Decimal("250000"), qualifying_children=2)
    # AGI 250k is 50k over the 200k single threshold -> 50 * $50 = $2,500 cut.
    assert r.child_tax_credit == Decimal("1900")


def test_additional_standard_deduction_and_senior_deduction_for_65_plus():
    r = calc(wages=Decimal("30000"), age_65_plus=True)
    assert r.additional_standard_deduction == Decimal("2000")
    assert r.senior_deduction == Decimal("6000")
    # 15,750 + 2,000 additional + 6,000 senior = 23,750 total deduction.
    assert r.deductions == Decimal("23750")
    assert r.taxable_income == Decimal("6250")


def test_qualified_dividends_and_ltcg_use_preferential_rates():
    r = calc(wages=Decimal("60000"), long_term_capital_gain=Decimal("20000"))
    # Preferential stacking saves money vs. taxing the gain as ordinary income.
    assert r.preferential_tax == Decimal("2385")
    assert r.income_tax_before_credits == Decimal("7460")
    regular_full = tax_liability(
        r.taxable_income, get_params(2025), FilingStatus.SINGLE
    )
    assert r.income_tax_before_credits < regular_full


def test_self_employment_tax_half_deduction_and_qbi():
    r = calc(self_employment_income=Decimal("50000"))
    assert r.self_employment_tax == Decimal("7065")
    assert r.adjustments == Decimal("3533")  # one-half of SE tax
    assert r.adjusted_gross_income == Decimal("46467")
    # QBI deduction = 20% of (net SE income) limited to 20% of taxable income.
    assert r.qbi_deduction == Decimal("6143")
    assert r.taxable_income == Decimal("24574")
    assert r.tax_due == Decimal("9776")  # income tax 2,711 + SE tax 7,065


def test_earned_income_credit_plateau_amounts():
    assert calc(wages=Decimal("9000")).earned_income_credit == Decimal("649")
    assert (
        calc(wages=Decimal("15000"), qualifying_children=1).earned_income_credit
        == Decimal("4328")
    )


def test_earned_income_credit_phases_out():
    r = calc(wages=Decimal("30000"), qualifying_children=2)
    assert r.earned_income_credit == Decimal("5752")  # past the plateau


def test_earned_income_credit_disqualified_by_investment_income():
    r = calc(
        wages=Decimal("15000"),
        qualifying_children=1,
        taxable_interest=Decimal("12000"),  # over the $11,950 limit
    )
    assert r.earned_income_credit == Decimal("0")


def test_earned_income_credit_is_refundable():
    r = calc(wages=Decimal("15000"), qualifying_children=1)
    # No tax due, but EITC + refundable CTC produce a refund.
    assert r.refund == Decimal("6028")


def test_excess_social_security_credit_requires_two_employers():
    base = dict(
        wages=Decimal("200000"),
        ss_tax_withheld=Decimal("13000"),
    )
    one = calc(**base, employer_count=1)
    two = calc(**base, employer_count=2)
    # Max SS = 176,100 * 6.2% = 10,918; excess only credited with 2+ employers.
    assert one.excess_ss_credit == Decimal("0")
    assert two.excess_ss_credit == Decimal("2082")


def test_capital_loss_is_limited_to_3000():
    r = calc(wages=Decimal("50000"), short_term_capital_gain=Decimal("-10000"))
    assert r.total_income == Decimal("47000")  # loss capped at -3,000


def test_amt_applies_with_preference_items():
    r = calc(wages=Decimal("200000"), amt_preference_items=Decimal("100000"))
    assert r.alternative_minimum_tax == Decimal("18027")
    # Regular income tax + AMT == the tentative minimum tax.
    assert r.federal_tax == Decimal("55094")


def test_amt_zero_for_ordinary_wage_earner():
    assert calc(wages=Decimal("120000")).alternative_minimum_tax == Decimal("0")


def test_american_opportunity_credit_partly_refundable():
    r = calc(
        wages=Decimal("50000"),
        qualified_tuition=Decimal("4000"),
        aotc_students=1,
    )
    # $2,500 max credit: 40% ($1,000) refundable, 60% ($1,500) nonrefundable.
    assert r.education_credits == Decimal("1500")
    assert r.refundable_education_credit == Decimal("1000")


def test_lifetime_learning_credit_without_aotc_students():
    r = calc(wages=Decimal("50000"), qualified_tuition=Decimal("10000"))
    assert r.education_credits == Decimal("2000")  # 20% of $10,000


def test_education_credit_phases_out():
    r = calc(
        wages=Decimal("95000"),
        qualified_tuition=Decimal("4000"),
        aotc_students=1,
    )
    assert r.education_credits == Decimal("0")
    assert r.refundable_education_credit == Decimal("0")


def test_savers_credit_is_limited_to_tax():
    r = calc(wages=Decimal("22000"), retirement_contributions=Decimal("2000"))
    # 50% rate on $2,000 = $1,000 potential, capped by the $628 of tax.
    assert r.savers_credit == Decimal("628")
    assert r.federal_tax == Decimal("0")


def test_social_security_partial_taxability():
    r = calc(taxable_pension_ira=Decimal("30000"), social_security_benefits=Decimal("20000"))
    assert r.taxable_social_security == Decimal("9600")
    assert r.total_income == Decimal("39600")


def test_capital_loss_carryover_and_carryforward():
    r = calc(wages=Decimal("50000"), capital_loss_carryover=Decimal("5000"))
    assert r.total_income == Decimal("47000")  # $3k of loss used this year
    assert r.capital_loss_carryforward == Decimal("2000")


def test_schedule_a_itemized_beats_standard_with_salt_cap():
    r = calc(
        wages=Decimal("150000"),
        salt_paid=Decimal("18000"),  # capped at $10,000
        mortgage_interest=Decimal("12000"),
        charitable_contributions=Decimal("5000"),
    )
    assert r.deductions == Decimal("27000")  # 10k + 12k + 5k
    assert r.taxable_income == Decimal("123000")


def test_qss_matches_mfj():
    qss = calc(filing_status=FilingStatus.QUALIFYING_SURVIVING_SPOUSE, wages=Decimal("120000"))
    mfj = calc(filing_status=FilingStatus.MARRIED_JOINTLY, wages=Decimal("120000"))
    assert qss.federal_tax == mfj.federal_tax
    assert qss.standard_deduction == Decimal("31500")


def test_k1_and_pension_flow_into_income():
    r = calc(partnership_income=Decimal("40000"), taxable_pension_ira=Decimal("10000"))
    assert r.total_income == Decimal("50000")


def test_unknown_tax_year_raises():
    with pytest.raises(ValueError):
        calc(tax_year=1999, wages=Decimal("50000"))


def test_dollars_uses_whole_dollar_rounding():
    assert dollars(Decimal("100.49")) == Decimal("100")
    assert dollars(Decimal("100.50")) == Decimal("101")
