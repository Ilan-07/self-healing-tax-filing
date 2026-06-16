from decimal import Decimal

from app.agents.reading.agent import ReadingAgent
from app.services.extraction import LabelAnchoredW2Parser


SINGLE_W2 = """
Form W-2 Wage and Tax Statement 2025
Employer identification number (EIN) 12-3456789
Employee SSN 123-45-6789
1 Wages, tips, other compensation        85000.00
2 Federal income tax withheld            11000.00
3 Social security wages                   85000.00
4 Social security tax withheld            5270.00
5 Medicare wages and tips                 85000.00
6 Medicare tax withheld                   1232.50
17 State income tax                        3500.00
"""


def test_label_anchored_parser_reads_w2_boxes():
    parsed = LabelAnchoredW2Parser().parse(ocr_text=SINGLE_W2)
    assert len(parsed) == 1
    w2 = parsed[0].w2
    assert w2.box1_wages == Decimal("85000.00")
    assert w2.box2_federal_withheld == Decimal("11000.00")
    assert w2.box4_ss_withheld == Decimal("5270.00")
    assert w2.box17_state_withheld == Decimal("3500.00")
    assert w2.employer_ein == "12-3456789"
    assert parsed[0].ssn == "123-45-6789"
    assert parsed[0].tax_year == 2025


def test_parser_tolerates_ocr_noise_and_missing_labels():
    # Comma thousands separator + an OCR space inside the cents.
    noisy = "1 Wages, tips, other compensation 1,234,567.89\nbox 2 9 876.54"
    parsed = LabelAnchoredW2Parser().parse(ocr_text=noisy)
    assert parsed[0].w2.box1_wages == Decimal("1234567.89")
    assert parsed[0].w2.box2_federal_withheld == Decimal("9876.54")


def test_parser_segments_multiple_w2s_by_ein():
    two = SINGLE_W2 + """
Employer identification number (EIN) 98-7654321
1 Wages, tips, other compensation        40000.00
2 Federal income tax withheld             4000.00
"""
    parsed = LabelAnchoredW2Parser().parse(ocr_text=two)
    assert len(parsed) == 2
    eins = {p.w2.employer_ein for p in parsed}
    assert eins == {"12-3456789", "98-7654321"}


def test_merge_combines_w2s_and_sums_income():
    from unittest.mock import Mock

    from app.schemas import FilingStatus, TaxpayerData, W2

    def one(wages, interest):
        d = TaxpayerData(
            employee_name="A",
            ssn="123-45-6789",
            filing_status=FilingStatus.SINGLE,
            w2s=[
                W2(
                    box1_wages=Decimal(wages),
                    box2_federal_withheld=Decimal("1000"),
                    box3_ss_wages=Decimal(wages),
                    box4_ss_withheld=Decimal(wages) * Decimal("0.062"),
                )
            ],
            taxable_interest=Decimal(interest),
        )
        d.aggregate_w2s()
        return d

    agent = ReadingAgent(Mock(), Mock(), Mock(), 0.0)
    merged = agent._merge([one("150000", "200"), one("100000", "300")])
    assert len(merged.w2s) == 2
    assert merged.wages == Decimal("250000")
    assert merged.employer_count == 2
    assert merged.taxable_interest == Decimal("500")


def test_positional_fallback_for_garbled_real_w2_form():
    # Real IRS W-2 forms: OCR garbles the labels ("tps", "oer") and the values
    # land on the EIN line. Box 1/2 must still be recovered positionally.
    text = (
        "1b Employer identfoation number Wages, tps, oer compensation "
        "Faderal came tax witheld\n98-5183738 140348.11 17995.3\n"
    )
    parsed = LabelAnchoredW2Parser().parse(ocr_text=text)
    assert len(parsed) == 1
    assert parsed[0].w2.box1_wages == Decimal("140348.11")
    assert parsed[0].w2.box2_federal_withheld == Decimal("17995.3")


def test_duplicate_w2_copies_are_deduplicated():
    from app.agents.reading.agent import _dedupe_w2s
    from app.schemas import W2
    from app.services.extraction.base import ParsedW2

    # Four copies (Copy B/C/2/2) of the SAME W-2 must collapse to one.
    copies = [
        ParsedW2(
            w2=W2(
                employer_ein="12-3456789",
                box1_wages=Decimal("44629.35"),
                box2_federal_withheld=Decimal("7631.62"),
            ),
            confidences={"box1_wages": 0.97},
        )
        for _ in range(4)
    ]
    deduped = _dedupe_w2s(copies)
    assert len(deduped) == 1

    # A genuinely different employer (different EIN) is preserved.
    copies.append(
        ParsedW2(
            w2=W2(employer_ein="98-7654321", box1_wages=Decimal("20000")),
            confidences={"box1_wages": 0.97},
        )
    )
    assert len(_dedupe_w2s(copies)) == 2


def test_scalar_model_confidence_is_normalized():
    assert ReadingAgent._model_confidence(95, "wages") == 0.95
    assert ReadingAgent._model_confidence(1, "wages") == 1
    assert ReadingAgent._model_confidence({"wages": "0.87"}, "wages") == 0.87
    assert ReadingAgent._model_confidence("invalid", "wages") == 0.8
