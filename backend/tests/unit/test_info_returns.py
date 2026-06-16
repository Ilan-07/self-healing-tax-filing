from decimal import Decimal

from app.services.extraction.info_returns import (
    classify_form,
    extract_information_returns,
)


def _fields(text):
    return {k: v for k, (v, _conf) in extract_information_returns(text).items()}


def test_classify_form():
    assert classify_form("Form 1099-INT Interest Income") == "1099-INT"
    assert classify_form("Schedule K-1 (Form 1065)") == "K-1"
    assert classify_form("SSA-1099 Social Security Benefit Statement") == "SSA-1099"
    assert classify_form("random text") == "unknown"


def test_multiple_1099_int_are_summed():
    text = """
    Form 1099-INT
    Interest income 1,200.00
    Form 1099-INT
    Interest income 800.00
    """
    assert _fields(text)["taxable_interest"] == Decimal("2000.00")


def test_1099_div_ordinary_qualified_and_capgain_distributions():
    text = """
    Form 1099-DIV
    1a Total ordinary dividends 3,000.00
    1b Qualified dividends 2,400.00
    2a Total capital gain distr. 500.00
    """
    f = _fields(text)
    assert f["ordinary_dividends"] == Decimal("3000.00")
    assert f["qualified_dividends"] == Decimal("2400.00")
    assert f["long_term_capital_gain"] == Decimal("500.00")


def test_1099_r_and_nec_and_ssa():
    text = """
    Form 1099-R
    1 Gross distribution 20000.00
    2a Taxable amount 15000.00
    Form 1099-NEC
    1 Nonemployee compensation 9000.00
    SSA-1099
    Net benefits 18000.00
    """
    f = _fields(text)
    assert f["taxable_pension_ira"] == Decimal("15000.00")
    assert f["self_employment_income"] == Decimal("9000.00")
    assert f["social_security_benefits"] == Decimal("18000.00")


def test_1099_b_summary_totals():
    text = """
    Form 1099-B
    Short-term transactions
    Proceeds 10,000.00 Cost basis 7,000.00
    Long-term transactions
    Proceeds 50,000.00 Cost basis 40,000.00
    """
    f = _fields(text)
    assert f["short_term_capital_gain"] == Decimal("3000.00")
    assert f["long_term_capital_gain"] == Decimal("10000.00")


def test_k1_routes_boxes_to_fields():
    text = """
    Schedule K-1 (Form 1065)
    1 Ordinary business income 25000.00
    5 Interest income 400.00
    6a Ordinary dividends 600.00
    9a Net long-term capital gain 1500.00
    """
    f = _fields(text)
    assert f["partnership_income"] == Decimal("25000.00")
    assert f["taxable_interest"] == Decimal("400.00")
    assert f["ordinary_dividends"] == Decimal("600.00")
    assert f["long_term_capital_gain"] == Decimal("1500.00")


def test_1098_mortgage_interest():
    text = "Form 1098 Mortgage Interest Statement\nMortgage interest received 12,500.00"
    assert _fields(text)["mortgage_interest"] == Decimal("12500.00")
