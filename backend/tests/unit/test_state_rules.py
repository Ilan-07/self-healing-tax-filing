from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import W2, FilingStatus, TaxCalculation, TaxpayerData
from app.schemas.tax import normalize_state
from app.state_rules import get_state_pack
from app.state_rules.validation import validate_all


def calc(**kwargs) -> TaxCalculation:
    defaults: dict = dict(tax_year=2025, filing_status=FilingStatus.SINGLE)
    defaults.update(kwargs)
    return TaxCalculator().calculate(TaxpayerData(**defaults))


def test_registry_is_structurally_valid():
    assert validate_all() == []


def test_no_pack_and_no_rate_yields_zero_state_tax():
    r = calc(wages=Decimal("80000"))  # default state="" -> no pack
    assert r.state_tax == Decimal("0")


def test_no_income_tax_state_has_no_pack():
    # Texas has no income tax: no pack installed, so the fallback applies.
    assert get_state_pack("TX", 2025) is None
    r = calc(wages=Decimal("80000"), state="TX")
    assert r.state_tax == Decimal("0")


def test_flat_rate_fallback_when_no_pack():
    # An uninstalled state with an explicit flat rate uses the fallback path.
    r = calc(wages=Decimal("80000"), state="ZZ", state_tax_rate=Decimal("0.05"))
    assert r.state_tax == Decimal("3213")  # 64,250 taxable * 5%


def test_colorado_flat_pack_overrides_on_federal_taxable_income():
    r = calc(wages=Decimal("80000"), state="CO")
    # CO: federal taxable income 64,250 * 4.40% flat.
    assert r.taxable_income == Decimal("64250")
    assert r.state_tax == Decimal("2827")


def test_pack_overrides_supplied_flat_rate():
    # CO pack must win over a supplied flat state_tax_rate.
    r = calc(wages=Decimal("80000"), state="CO", state_tax_rate=Decimal("0.99"))
    assert r.state_tax == Decimal("2827")


def test_california_progressive_pack():
    r = calc(wages=Decimal("80000"), state="CA")
    # AGI 80,000 - CA std 5,540 = 74,460 of CA taxable income, taxed 1%-9.3%.
    pack = get_state_pack("CA", 2025)
    assert pack is not None
    assert Decimal("3000") < r.state_tax < Decimal("4000")
    assert any("CA:" in line for line in r.trace)


def test_new_hampshire_custom_base_runs_but_is_repealed_for_2025():
    r = calc(
        wages=Decimal("80000"),
        state="NH",
        taxable_interest=Decimal("5000"),
        ordinary_dividends=Decimal("3000"),
    )
    # I&D Tax repealed effective 2025 -> 0, but the custom path still runs.
    assert r.state_tax == Decimal("0")
    assert any("NH:" in line for line in r.trace)


def test_unverified_pack_emits_trace_note():
    r = calc(wages=Decimal("80000"), state="CO")
    assert any("[unverified] CO" in line for line in r.trace)


def test_pennsylvania_flat_on_agi():
    r = calc(wages=Decimal("80000"), state="PA")
    # PA 3.07% of federal AGI (80,000, no adjustments); no state std deduction.
    assert r.adjusted_gross_income == Decimal("80000")
    assert r.state_tax == Decimal("2456")  # 80,000 * 3.07%


def test_north_carolina_applies_state_standard_deduction():
    r = calc(wages=Decimal("80000"), state="NC")
    # NC 4.25% of (AGI 80,000 - single std 12,750) = 67,250.
    assert r.state_tax == Decimal("2858")  # 67,250 * 4.25%


def test_mississippi_exempts_first_10k():
    r = calc(wages=Decimal("80000"), state="MS")
    # AGI 80,000: first 10,000 at 0%, remaining 70,000 at 4.4%.
    assert r.state_tax == Decimal("3080")


def test_georgia_applies_state_standard_deduction():
    r = calc(wages=Decimal("80000"), state="GA")
    # GA 5.19% of (AGI 80,000 - single std 12,000) = 68,000.
    assert r.state_tax == Decimal("3529")  # 68,000 * 5.19%


def test_idaho_flat_on_federal_taxable_income():
    r = calc(wages=Decimal("80000"), state="ID")
    # ID 5.3% of federal taxable income 64,250.
    assert r.taxable_income == Decimal("64250")
    assert r.state_tax == Decimal("3405")  # 64,250 * 5.3%


def test_iowa_flat_on_agi():
    r = calc(wages=Decimal("80000"), state="IA")
    assert r.state_tax == Decimal("3040")  # 80,000 AGI * 3.8%


def test_louisiana_flat_on_agi():
    r = calc(wages=Decimal("80000"), state="LA")
    assert r.state_tax == Decimal("2400")  # 80,000 AGI * 3.0%


def test_massachusetts_flat_below_surtax_threshold():
    r = calc(wages=Decimal("80000"), state="MA")
    assert r.state_tax == Decimal("4000")  # 80,000 * 5%, below $1.083M surtax


def test_massachusetts_surtax_applies_above_threshold():
    r = calc(wages=Decimal("2000000"), state="MA")
    # 5% on first 1,083,150 + 9% on the remaining 916,850.
    assert r.state_tax == Decimal("136674")


def test_new_jersey_reference_pack_schedule():
    # NJ is overridden by the tenforty-backed pack in the live registry (see
    # test_state_rules_tenforty.py); this exercises the reference pack directly,
    # which remains the fallback. Federal AGI 80,000 through NJ single schedule.
    from app.state_rules.base import FederalContext
    from app.state_rules.states import new_jersey_2025

    federal = FederalContext(
        filing_status=FilingStatus.SINGLE,
        agi=Decimal("80000"),
        taxable_income=Decimal("64250"),
    )
    result = new_jersey_2025.PACK.compute(
        TaxpayerData(tax_year=2025, state="NJ"), federal
    )
    assert result.tax == Decimal("2970")


def test_ohio_zero_bracket_then_2_75_percent():
    r = calc(wages=Decimal("80000"), state="OH")
    # First 26,050 untaxed; (80,000 - 26,050) = 53,950 at 2.75%.
    assert r.state_tax == Decimal("1484")


def test_ohio_just_above_zero_bracket():
    r = calc(wages=Decimal("30000"), state="OH")
    # AGI 30,000: only the 3,950 above the 26,050 zero bracket is taxed at 2.75%.
    assert r.state_tax == Decimal("109")


def test_virginia_progressive_with_standard_deduction():
    r = calc(wages=Decimal("80000"), state="VA")
    # AGI 80,000 - VA single std 8,500 = 71,500 through the 2%-5.75% schedule.
    assert r.state_tax == Decimal("3854")
    assert any("VA:" in line for line in r.trace)


def test_maryland_state_only_progressive():
    r = calc(wages=Decimal("80000"), state="MD")
    # AGI 80,000 - MD max single std 2,700 = 77,300; state tax only (no county).
    assert r.state_tax == Decimal("3619")


def test_minnesota_progressive_on_federal_taxable_income():
    r = calc(wages=Decimal("80000"), state="MN")
    # MN starts from federal taxable income 64,250 (5.35% then 6.8%).
    assert r.taxable_income == Decimal("64250")
    assert r.state_tax == Decimal("3909")


def test_wisconsin_progressive_single():
    r = calc(wages=Decimal("80000"), state="WI")
    # Federal AGI 80,000 through WI single schedule (3.5%/4.4%/5.3%); the
    # phased-out standard deduction is not modeled.
    assert r.state_tax == Decimal("3844")


def test_missouri_progressive_on_federal_taxable_income():
    r = calc(wages=Decimal("80000"), state="MO")
    # MO starts from federal taxable income 64,250; small graduated bands then
    # 4.7% top rate.
    assert r.taxable_income == Decimal("64250")
    assert r.state_tax == Decimal("2849")


def test_south_carolina_progressive_on_federal_taxable_income():
    r = calc(wages=Decimal("80000"), state="SC")
    # Federal taxable income 64,250: 0% / 3% / 6.2% top.
    assert r.taxable_income == Decimal("64250")
    assert r.state_tax == Decimal("3325")


def test_oregon_progressive_with_standard_deduction():
    r = calc(wages=Decimal("80000"), state="OR")
    # AGI 80,000 - OR single std 2,745 = 77,255 through the 4.75%-8.75% bands;
    # the federal-tax-liability subtraction is not modeled.
    assert r.state_tax == Decimal("6459")


def test_connecticut_progressive_single():
    r = calc(wages=Decimal("80000"), state="CT")
    # Federal AGI 80,000 through CT single schedule (2% / 4.5% / 5.5%);
    # the personal-exemption phase-out and recapture are not modeled.
    assert r.state_tax == Decimal("3650")


def test_batch_c_single_filer_reference_amounts():
    # One reference scenario ($80k single) per Batch C jurisdiction. base=AGI
    # states use AGI 80,000 (less any state std deduction); base=federal taxable
    # income states use 64,250.
    expected = {
        "AL": Decimal("3960"),
        "AR": Decimal("3120"),
        "DE": Decimal("4049"),
        "HI": Decimal("5672"),
        "KS": Decimal("4175"),
        "ME": Decimal("4100"),
        "MT": Decimal("3545"),
        "NE": Decimal("3289"),
        "NM": Decimal("2869"),
        "ND": Decimal("333"),
        "OK": Decimal("3310"),
        "RI": Decimal("2604"),
        "VT": Decimal("2765"),
        "WV": Decimal("3208"),
        "DC": Decimal("3861"),
    }
    for state, amount in expected.items():
        r = calc(wages=Decimal("80000"), state=state)
        assert r.state_tax == amount, f"{state}: {r.state_tax} != {amount}"


def test_normalize_state_handles_names_codes_and_junk():
    assert normalize_state("California") == "CA"
    assert normalize_state("  california ") == "CA"
    assert normalize_state("ca") == "CA"
    assert normalize_state("D.C.") == "DC"
    assert normalize_state("") == ""
    assert normalize_state(None) == ""
    # Unknown values are upper-cased and pass through (no pack match -> safe).
    assert normalize_state("Freedonia") == "FREEDONIA"
    assert get_state_pack(normalize_state("Freedonia"), 2025) is None


def test_state_derived_from_w2_drives_state_tax():
    # The pipeline never sets data.state directly; it must come from the W-2.
    data = TaxpayerData(
        tax_year=2025,
        filing_status=FilingStatus.SINGLE,
        w2s=[
            W2(box1_wages=Decimal("80000"), box15_state="co",
               box17_state_withheld=Decimal("2000")),
        ],
    )
    data.aggregate_w2s()
    assert data.state == "CO"
    r = TaxCalculator().calculate(data)
    assert r.state_tax == Decimal("2827")  # CO 4.40% of 64,250 taxable income


def test_primary_state_is_the_one_with_most_withholding():
    data = TaxpayerData(
        tax_year=2025,
        filing_status=FilingStatus.SINGLE,
        w2s=[
            W2(box1_wages=Decimal("30000"), box15_state="PA",
               box17_state_withheld=Decimal("500")),
            W2(box1_wages=Decimal("50000"), box15_state="CO",
               box17_state_withheld=Decimal("1800")),
        ],
    )
    data.aggregate_w2s()
    assert data.state == "CO"  # larger state withholding wins


def test_case_insensitive_and_no_tax_states():
    assert calc(wages=Decimal("80000"), state="co").state_tax == Decimal("2827")
    for no_tax in ("TX", "FL", "WA", "WY", "AK", "NV", "SD", "TN"):
        assert get_state_pack(no_tax, 2025) is None
