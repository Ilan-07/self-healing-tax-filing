"""Real-document end-to-end: a generated W-2 (PDF text layer and a raster PNG
run through live Tesseract OCR) flows through the actual ReadingAgent ->
TaxCalculator -> Form 1040 PDF, and the extracted/computed numbers are checked
against the values baked into the document.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.agents.reading.agent import ReadingAgent
from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    FilingReceipt,
    SubmissionResult,
    VerificationResult,
    WorkflowStatus,
)
from app.services.documents.service import DocumentService
from app.services.ocr.service import OCRService
from app.services.pdf.form1040 import Form1040Service


W2_LINES = [
    "Form W-2 Wage and Tax Statement 2025",
    "Employer identification number (EIN) 12-3456789",
    "Employee SSN 123-45-6789",
    "1 Wages, tips, other compensation 85000.00",
    "2 Federal income tax withheld 11000.00",
    "3 Social security wages 85000.00",
    "4 Social security tax withheld 5270.00",
    "5 Medicare wages and tips 85000.00",
    "6 Medicare tax withheld 1232.50",
    "17 State income tax 3500.00",
]


class _StubOllama:
    """No vision model in tests; force the deterministic OCR/parser path."""

    def extract_tax_fields(self, image, text):
        return {}

    def classify_remediation(self, errors):
        return {}


def _reading_agent() -> ReadingAgent:
    return ReadingAgent(DocumentService(), OCRService(), _StubOllama(), 0.0)


def _write_w2_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    y = 720
    for line in W2_LINES:
        c.drawString(72, y, line)
        y -= 26
    c.save()


def _write_pdf(path, lines) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    y = 720
    for line in lines:
        c.drawString(72, y, line)
        y -= 24
    c.save()


# Each: (document lines, {taxpayer_field: expected amount}).
INFO_RETURNS = {
    "1099-INT": (
        ["Form 1099-INT", "1 Interest income 1,200.00"],
        {"taxable_interest": "1200.00"},
    ),
    "1099-DIV": (
        [
            "Form 1099-DIV",
            "1a Total ordinary dividends 3,000.00",
            "1b Qualified dividends 2,400.00",
            "2a Total capital gain distr. 500.00",
        ],
        {
            "ordinary_dividends": "3000.00",
            "qualified_dividends": "2400.00",
            "long_term_capital_gain": "500.00",
        },
    ),
    "1099-R": (
        ["Form 1099-R", "1 Gross distribution 20,000.00", "2a Taxable amount 15,000.00"],
        {"taxable_pension_ira": "15000.00"},
    ),
    "1099-NEC": (
        ["Form 1099-NEC", "1 Nonemployee compensation 9,000.00"],
        {"self_employment_income": "9000.00"},
    ),
    "SSA-1099": (
        ["Form SSA-1099", "Box 5 Net benefits 18,000.00"],
        {"social_security_benefits": "18000.00"},
    ),
    "1099-B": (
        [
            "Form 1099-B",
            "Short-term transactions Proceeds 10,000.00 Cost basis 7,000.00",
            "Long-term transactions Proceeds 50,000.00 Cost basis 40,000.00",
        ],
        {
            "short_term_capital_gain": "3000.00",
            "long_term_capital_gain": "10000.00",
        },
    ),
    "K-1": (
        [
            "Schedule K-1 (Form 1065)",
            "1 Ordinary business income 25,000.00",
            "5 Interest income 400.00",
            "6a Ordinary dividends 600.00",
            "9a Net long-term capital gain 1,500.00",
        ],
        {
            "partnership_income": "25000.00",
            "taxable_interest": "400.00",
            "ordinary_dividends": "600.00",
            "long_term_capital_gain": "1500.00",
        },
    ),
    "1098": (
        ["Form 1098 Mortgage Interest Statement", "Mortgage interest received 12,500.00"],
        {"mortgage_interest": "12500.00"},
    ),
    "1098-T": (
        ["Form 1098-T Tuition Statement", "1 Payments received for qualified tuition 4,000.00"],
        {"qualified_tuition": "4000.00"},
    ),
}


@pytest.mark.parametrize("form", list(INFO_RETURNS))
def test_information_return_end_to_end(tmp_path, form):
    lines, expected = INFO_RETURNS[form]
    pdf = tmp_path / f"{form}.pdf"
    _write_pdf(pdf, lines)

    data, _raw, _logs = _reading_agent().run(pdf)
    for field, value in expected.items():
        assert getattr(data, field) == Decimal(value), f"{form}.{field}"

    # The engine accepts the extracted return without error.
    TaxCalculator().calculate(data)


def test_multi_document_submission_merges_w2_and_1099s(tmp_path):
    w2 = tmp_path / "w2.pdf"
    _write_w2_pdf(w2)
    int_doc = tmp_path / "int.pdf"
    _write_pdf(int_doc, ["Form 1099-INT", "1 Interest income 1,200.00"])
    div_doc = tmp_path / "div.pdf"
    _write_pdf(div_doc, ["Form 1099-DIV", "1a Total ordinary dividends 3,000.00"])

    data, _raw, _logs = _reading_agent().run_many([w2, int_doc, div_doc])
    assert data.wages == Decimal("85000.00")
    assert data.taxable_interest == Decimal("1200.00")
    assert data.ordinary_dividends == Decimal("3000.00")

    calc = TaxCalculator().calculate(data)
    assert calc.total_income == Decimal("89200")  # 85,000 + 1,200 + 3,000


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="Tesseract OCR not installed"
)
def test_1099_int_raster_via_real_ocr(tmp_path):
    png = tmp_path / "1099int.png"
    _write_png(png, ["Form 1099-INT", "1 Interest income 1200.00"])
    data, _raw, _logs = _reading_agent().run(png)
    assert data.taxable_interest == Decimal("1200.00")


def _write_png(path, lines) -> None:
    img = Image.new("RGB", (1400, 300), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    y = 30
    for line in lines:
        draw.text((30, y), line, fill="black", font=font)
        y += 60
    img.save(str(path))


def _write_w2_png(path) -> None:
    img = Image.new("RGB", (1400, 700), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    y = 30
    for line in W2_LINES:
        draw.text((30, y), line, fill="black", font=font)
        y += 60
    img.save(str(path))


def _assert_w2_extraction(data) -> None:
    assert data.wages == Decimal("85000.00")
    assert data.federal_tax_withheld == Decimal("11000.00")
    assert data.ss_wages == Decimal("85000.00")
    assert data.employer_count == 1
    assert data.ssn == "123-45-6789"


def test_end_to_end_pdf_text_layer_to_1040(tmp_path):
    pdf = tmp_path / "w2.pdf"
    _write_w2_pdf(pdf)

    data, raw_text, _logs = _reading_agent().run(pdf)
    _assert_w2_extraction(data)

    calc = TaxCalculator().calculate(data)
    assert calc.adjusted_gross_income == Decimal("85000")
    assert calc.taxable_income == Decimal("69250")  # 85,000 - 15,750

    result = SubmissionResult(
        submission_id="e2e-1",
        status=WorkflowStatus.COMPLETED,
        original_filename="w2.pdf",
        extracted_data=data,
        calculation=calc,
        verification=VerificationResult(valid=True, confidence_score=0.99, checks=[]),
    )
    receipt = FilingReceipt(
        submission_id="e2e-1",
        reference_number="ACK1",
        timestamp=datetime.now(timezone.utc),
        filing_status="accepted",
    )
    out = Form1040Service().generate(result, receipt, tmp_path / "1040.pdf")
    assert out.read_bytes().startswith(b"%PDF-")


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="Tesseract OCR not installed"
)
def test_end_to_end_raster_image_via_real_ocr(tmp_path):
    png = tmp_path / "w2.png"
    _write_w2_png(png)

    # No text layer -> this exercises the real Tesseract OCR path.
    data, raw_text, _logs = _reading_agent().run(png)

    assert "wages" in raw_text.lower()
    assert data.wages == Decimal("85000.00")
    assert data.federal_tax_withheld == Decimal("11000.00")

    calc = TaxCalculator().calculate(data)
    assert calc.taxable_income == Decimal("69250")
