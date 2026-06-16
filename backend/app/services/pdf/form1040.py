"""Render a faithful, line-numbered IRS Form 1040 (plus the schedules a return
actually used) from the engine output.

This is a self-contained facsimile -- official layout, real line numbers, whole
dollars, boxed amounts -- not an overlay on the IRS PDF, so it runs offline and
maps every value to the line a preparer would expect.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas import FilingReceipt, FilingStatus, SubmissionResult, TaxpayerData
from app.schemas.tax import TaxCalculation

ZERO = Decimal("0")
INK = colors.HexColor("#111111")
BAND = colors.HexColor("#1f3a5f")
BAND_TEXT = colors.white
RULE = colors.HexColor("#8a8a8a")
BOX = colors.HexColor("#c9c9c9")
SUBTLE = colors.HexColor("#f1f4f8")

LINE_COL = 0.55 * inch
DESC_COL = 5.35 * inch
AMT_COL = 1.40 * inch

_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, textColor=INK)
_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, textColor=INK)
_RIGHT = ParagraphStyle(
    "r", fontName="Helvetica-Bold", fontSize=10, textColor=INK, alignment=2
)
_SMALL = ParagraphStyle("sm", fontName="Helvetica", fontSize=8, textColor=INK)


def money(value: Decimal | int | None) -> str:
    if value is None:
        return ""
    d = Decimal(value).quantize(Decimal("1"))
    return f"({abs(d):,})" if d < 0 else f"{d:,}"


def _checkbox(selected: bool, label: str) -> str:
    # ASCII markers render reliably in the base-14 fonts (unlike ☒/☐).
    mark = "[X]" if selected else "[&nbsp;&nbsp;]"
    weight = ("<b>", "</b>") if selected else ("", "")
    return f"{mark} {weight[0]}{label}{weight[1]}"


class Form1040Service:
    def generate(
        self,
        result: SubmissionResult,
        receipt: FilingReceipt,
        output: Path,
    ) -> Path:
        data = result.extracted_data or TaxpayerData()
        calc = result.calculation
        output.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output),
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.55 * inch,
            bottomMargin=0.6 * inch,
            title=f"Form 1040 ({data.tax_year})",
        )
        story = self._header(data, receipt)
        story += self._filing_status(data)
        if calc is not None:
            story += self._income(data, calc)
            story += self._tax_and_payments(data, calc)
            story += self._schedules(data, calc)
        doc.build(story, onFirstPage=self._frame, onLaterPages=self._frame)
        return output

    # ---- page 1: masthead + taxpayer ----
    def _header(self, data: TaxpayerData, receipt: FilingReceipt) -> list:
        masthead = Table(
            [[
                Paragraph("Form <b>1040</b>", _TITLE),
                Paragraph(
                    "U.S. Individual Income Tax Return", _SUB
                ),
                Paragraph(
                    f"<b>{data.tax_year}</b><br/>OMB No. 1545-0074", _RIGHT
                ),
            ]],
            colWidths=[1.4 * inch, 4.5 * inch, 1.4 * inch],
        )
        masthead.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.4, INK),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        taxpayer = Table(
            [
                ["Name", data.employee_name or "—", "SSN", data.masked_ssn or "—"],
                [
                    "Reference",
                    receipt.reference_number,
                    "Status",
                    receipt.filing_status.replace("_", " "),
                ],
            ],
            colWidths=[0.9 * inch, 4.0 * inch, 0.7 * inch, 1.7 * inch],
        )
        taxpayer.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
                    ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8.5),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("BOX", (0, 0), (-1, -1), 0.5, BOX),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BOX),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return [masthead, Spacer(1, 6), taxpayer, Spacer(1, 8)]

    def _filing_status(self, data: TaxpayerData) -> list:
        fs = data.filing_status
        labels = [
            (FilingStatus.SINGLE, "Single"),
            (FilingStatus.MARRIED_JOINTLY, "Married filing jointly"),
            (FilingStatus.MARRIED_SEPARATELY, "Married filing separately"),
            (FilingStatus.HEAD_OF_HOUSEHOLD, "Head of household"),
            (FilingStatus.QUALIFYING_SURVIVING_SPOUSE, "Qualifying surviving spouse"),
        ]
        text = "   ".join(_checkbox(fs == value, label) for value, label in labels)
        dep = (
            f"Dependents — qualifying children: {data.qualifying_children}   "
            f"other dependents: {data.other_dependents}"
        )
        return [
            self._band("Filing Status"),
            Paragraph(text, _SMALL),
            Spacer(1, 2),
            Paragraph(dep, _SMALL),
            Spacer(1, 6),
        ]

    # ---- income / AGI / deductions / taxable income ----
    def _income(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        cap_gain = (
            data.long_term_capital_gain
            + data.short_term_capital_gain
            - data.capital_loss_carryover
        )
        sched1_income = (
            data.self_employment_income
            + data.partnership_income
            + data.other_income
        )
        rows = [
            ("1a", "Total amount from Form(s) W-2, box 1 (wages)", data.wages, False),
            ("2a", "Tax-exempt interest", data.tax_exempt_interest, False),
            ("2b", "Taxable interest", data.taxable_interest, False),
            ("3a", "Qualified dividends", data.qualified_dividends, False),
            ("3b", "Ordinary dividends", data.ordinary_dividends, False),
            ("5b", "Pensions and annuities (taxable)", data.taxable_pension_ira, False),
            ("6a", "Social security benefits", data.social_security_benefits, False),
            ("6b", "Taxable amount", calc.taxable_social_security, False),
            ("7", "Capital gain or (loss)", cap_gain, False),
            ("8", "Additional income from Schedule 1, line 10", sched1_income, False),
            ("9", "Total income", calc.total_income, True),
            ("10", "Adjustments to income (Schedule 1, line 25)", calc.adjustments, False),
            ("11", "Adjusted gross income", calc.adjusted_gross_income, True),
            ("12", "Standard deduction or itemized deductions", calc.deductions, False),
            ("13", "Qualified business income deduction (Form 8995)", calc.qbi_deduction, False),
            ("14", "Add lines 12 and 13", calc.deductions + calc.qbi_deduction, False),
            ("15", "Taxable income", calc.taxable_income, True),
        ]
        return [self._band("Income"), self._lines(rows), Spacer(1, 6)]

    def _tax_and_payments(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        line18 = calc.income_tax_before_credits + calc.alternative_minimum_tax
        line21 = calc.child_tax_credit + calc.other_dependent_credit + calc.education_credits + calc.savers_credit
        line22 = max(ZERO, line18 - line21)
        sched2_other = (
            calc.self_employment_tax
            + calc.additional_medicare_tax
            + calc.net_investment_income_tax
        )
        refundable = (
            calc.earned_income_credit
            + calc.refundable_child_tax_credit
            + calc.refundable_education_credit
            + calc.excess_ss_credit
        )
        line33 = data.federal_tax_withheld + data.estimated_payments + refundable
        federal_tax = calc.federal_tax
        refund = max(ZERO, line33 - federal_tax)
        owe = max(ZERO, federal_tax - line33)
        tax_rows = [
            ("16", "Tax (Tax Table / Tax Computation Worksheet)", calc.income_tax_before_credits, False),
            ("17", "Amount from Schedule 2, line 3 (AMT)", calc.alternative_minimum_tax, False),
            ("18", "Add lines 16 and 17", line18, False),
            ("19", "Child tax credit / credit for other dependents", calc.child_tax_credit + calc.other_dependent_credit, False),
            ("20", "Amount from Schedule 3, line 8", calc.education_credits + calc.savers_credit, False),
            ("21", "Add lines 19 and 20", line21, False),
            ("22", "Subtract line 21 from line 18", line22, False),
            ("23", "Other taxes from Schedule 2, line 21", sched2_other, False),
            ("24", "Total tax", federal_tax, True),
        ]
        pay_rows = [
            ("25a", "Federal income tax withheld from W-2", data.federal_tax_withheld, False),
            ("26", "2025 estimated tax payments", data.estimated_payments, False),
            ("27", "Earned income credit (EIC)", calc.earned_income_credit, False),
            ("28", "Additional child tax credit (Schedule 8812)", calc.refundable_child_tax_credit, False),
            ("29", "American opportunity credit (refundable)", calc.refundable_education_credit, False),
            ("31", "Amount from Schedule 3, line 13 (excess SS)", calc.excess_ss_credit, False),
            ("33", "Total payments", line33, True),
        ]
        result_rows = [
            ("34", "Overpayment (refund)", refund, True),
            ("37", "Amount you owe", owe, True),
        ]
        return [
            self._band("Tax and Credits"),
            self._lines(tax_rows),
            Spacer(1, 6),
            self._band("Payments"),
            self._lines(pay_rows),
            Spacer(1, 6),
            self._band("Refund / Amount You Owe"),
            self._lines(result_rows),
        ]

    # ---- conditional schedules ----
    def _schedules(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        out: list = []
        out += self._schedule_1(data, calc)
        out += self._schedule_2(calc)
        out += self._schedule_3(calc)
        out += self._schedule_a(data, calc)
        out += self._schedule_b(data)
        out += self._schedule_se(data, calc)
        out += self._form_8995(calc)
        return out

    def _schedule_1(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        income = (
            data.self_employment_income
            + data.partnership_income
            + data.other_income
        )
        if income <= 0 and calc.adjustments <= 0:
            return []
        rows = [
            ("3", "Business income (Schedule C)", data.self_employment_income, False),
            ("5", "Rental, royalty, partnership, S-corp (Schedule E)", data.partnership_income, False),
            ("8", "Other income", data.other_income, False),
            ("10", "Total additional income", income, True),
            ("15", "Deductible part of self-employment tax", calc.adjustments, False),
            ("25", "Total adjustments to income", calc.adjustments, True),
        ]
        return self._schedule("Schedule 1", "Additional Income and Adjustments", rows)

    def _schedule_2(self, calc: TaxCalculation) -> list:
        other = (
            calc.self_employment_tax
            + calc.additional_medicare_tax
            + calc.net_investment_income_tax
        )
        if calc.alternative_minimum_tax <= 0 and other <= 0:
            return []
        rows = [
            ("1", "Alternative minimum tax (Form 6251)", calc.alternative_minimum_tax, False),
            ("3", "Add lines 1 and 2", calc.alternative_minimum_tax, True),
            ("4", "Self-employment tax (Schedule SE)", calc.self_employment_tax, False),
            ("11", "Additional Medicare Tax (Form 8959)", calc.additional_medicare_tax, False),
            ("12", "Net investment income tax (Form 8960)", calc.net_investment_income_tax, False),
            ("21", "Total other taxes", other, True),
        ]
        return self._schedule("Schedule 2", "Additional Taxes", rows)

    def _schedule_3(self, calc: TaxCalculation) -> list:
        if calc.education_credits <= 0 and calc.savers_credit <= 0 and calc.excess_ss_credit <= 0:
            return []
        rows = [
            ("3", "Education credits (Form 8863)", calc.education_credits, False),
            ("4", "Retirement savings contributions credit (Form 8880)", calc.savers_credit, False),
            ("8", "Total nonrefundable credits", calc.education_credits + calc.savers_credit, True),
            ("11", "Excess Social Security tax withheld", calc.excess_ss_credit, False),
            ("13", "Total other payments / refundable credits", calc.excess_ss_credit, True),
        ]
        return self._schedule("Schedule 3", "Additional Credits and Payments", rows)

    def _schedule_a(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        std_stack = calc.standard_deduction + calc.additional_standard_deduction
        itemizing = (calc.deductions - calc.senior_deduction) > std_stack
        if not itemizing:
            return []  # standard deduction was used; no Schedule A filed
        salt = min(data.salt_paid, Decimal("10000"))
        medical = max(ZERO, data.medical_expenses - Decimal("0.075") * calc.adjusted_gross_income)
        charitable = min(data.charitable_contributions, Decimal("0.60") * calc.adjusted_gross_income)
        total = salt + data.mortgage_interest + medical + charitable
        rows = [
            ("1", "Medical expenses over 7.5% of AGI", medical, False),
            ("7", "State and local taxes (limited to $10,000)", salt, False),
            ("8e", "Home mortgage interest", data.mortgage_interest, False),
            ("14", "Gifts to charity", charitable, False),
            ("17", "Total itemized deductions", total, True),
        ]
        return self._schedule("Schedule A", "Itemized Deductions", rows)

    def _schedule_b(self, data: TaxpayerData) -> list:
        if data.taxable_interest + data.ordinary_dividends <= Decimal("1500"):
            return []
        rows = [
            ("2", "Total taxable interest", data.taxable_interest, True),
            ("6", "Total ordinary dividends", data.ordinary_dividends, True),
        ]
        return self._schedule("Schedule B", "Interest and Ordinary Dividends", rows)

    def _schedule_se(self, data: TaxpayerData, calc: TaxCalculation) -> list:
        if calc.self_employment_tax <= 0:
            return []
        net = (data.self_employment_income * Decimal("0.9235")).quantize(Decimal("1"))
        rows = [
            ("3", "Net profit from self-employment", data.self_employment_income, False),
            ("4", "Net earnings (92.35%)", net, False),
            ("12", "Self-employment tax", calc.self_employment_tax, True),
            ("13", "Deduction for one-half of SE tax", (calc.self_employment_tax / 2).quantize(Decimal("1")), False),
        ]
        return self._schedule("Schedule SE", "Self-Employment Tax", rows)

    def _form_8995(self, calc: TaxCalculation) -> list:
        if calc.qbi_deduction <= 0:
            return []
        rows = [
            ("5", "Qualified business income component", calc.qbi_deduction, False),
            ("15", "Qualified business income deduction", calc.qbi_deduction, True),
        ]
        return self._schedule("Form 8995", "Qualified Business Income Deduction", rows)

    # ---- shared building blocks ----
    def _schedule(self, code: str, title: str, rows: list) -> list:
        from reportlab.platypus import PageBreak

        head = Table(
            [[Paragraph(f"<b>{code}</b> (Form 1040)", _TITLE), Paragraph(title, _RIGHT)]],
            colWidths=[3.0 * inch, 4.3 * inch],
        )
        head.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.4, INK),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return [PageBreak(), head, Spacer(1, 8), self._lines(rows)]

    @staticmethod
    def _band(title: str):
        band = Table([[title]], colWidths=[LINE_COL + DESC_COL + AMT_COL])
        band.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), BAND),
                    ("TEXTCOLOR", (0, 0), (-1, -1), BAND_TEXT),
                    ("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 9.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return band

    @staticmethod
    def _lines(rows: list) -> Table:
        data = [[no, desc, money(amt)] for no, desc, amt, _bold in rows]
        table = Table(data, colWidths=[LINE_COL, DESC_COL, AMT_COL])
        style = [
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
            ("FONT", (1, 0), (1, -1), "Helvetica", 8.5),
            ("FONT", (2, 0), (2, -1), "Courier", 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, BOX),
            ("BOX", (2, 0), (2, -1), 0.5, BOX),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (1, 0), (1, -1), 4),
        ]
        for i, (_no, _desc, _amt, bold) in enumerate(rows):
            if bold:
                style += [
                    ("FONT", (1, i), (2, i), "Helvetica-Bold", 9),
                    ("BACKGROUND", (0, i), (-1, i), SUBTLE),
                    ("LINEABOVE", (0, i), (-1, i), 0.7, RULE),
                ]
        table.setStyle(TableStyle(style))
        return table

    @staticmethod
    def _frame(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(0.6 * inch, 0.5 * inch, 8.0 * inch, 0.5 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(RULE)
        canvas.drawString(0.6 * inch, 0.36 * inch, "Form 1040 (2025) — generated; review before filing")
        canvas.drawRightString(8.0 * inch, 0.36 * inch, f"Page {doc.page}")
        canvas.restoreState()
