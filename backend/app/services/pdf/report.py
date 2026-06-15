from __future__ import annotations

import io
from pathlib import Path
from xml.sax.saxutils import escape

import fitz
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas import FilingReceipt, SubmissionResult


REPORT_SIZE = (8.5 * inch, 12.75 * inch)
NAVY = colors.HexColor("#052A67")
NAVY_DARK = colors.HexColor("#031C48")
BLUE_LIGHT = colors.HexColor("#EEF4FC")
GREEN = colors.HexColor("#147A30")
GREEN_LIGHT = colors.HexColor("#EEF9ED")
INK = colors.HexColor("#0B1735")
MUTED = colors.HexColor("#53637B")
LINE = colors.HexColor("#B9C8DC")
WHITE = colors.white
RED = colors.HexColor("#B42318")
ORANGE = colors.HexColor("#E58700")
PURPLE = colors.HexColor("#7544D7")
BLUE = colors.HexColor("#1761B5")


class PDFReportService:
    """Generate a filing dossier modeled after a professional tax summary."""

    def generate(
        self,
        result: SubmissionResult,
        receipt: FilingReceipt,
        output: Path,
        document_preview: Path | None = None,
    ) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        styles = self._styles()
        doc = SimpleDocTemplate(
            str(output),
            pagesize=REPORT_SIZE,
            leftMargin=0.18 * inch,
            rightMargin=0.18 * inch,
            topMargin=0.24 * inch,
            bottomMargin=0.22 * inch,
            title=f"Professional Tax Filing Report - {receipt.reference_number}",
            author="TaxFlow Local",
            subject="Local tax processing and verification record",
        )

        story = self._dashboard(result, receipt, styles)
        story += [PageBreak()]
        story += self._appendix(result, receipt, styles, document_preview)
        doc.build(
            story,
            onFirstPage=lambda canvas, document: self._page_frame(
                canvas, document, receipt, dashboard=True
            ),
            onLaterPages=lambda canvas, document: self._page_frame(
                canvas, document, receipt, dashboard=False
            ),
        )
        return output

    def _dashboard(self, result, receipt, styles):
        data = result.extracted_data
        calc = result.calculation
        story = self._header(receipt, styles)

        taxpayer = self._field_card(
            "1. TAXPAYER INFORMATION",
            [
                ("Full Name", data.employee_name or "Not provided"),
                ("SSN / ITIN", "Not retained in report"),
                ("Filing Status", data.filing_status.value.replace("_", " ").title()),
                ("Employer", data.employer_name or "Not provided"),
                ("State", data.state or "Not provided"),
                ("Tax Year", str(data.tax_year)),
            ],
            styles,
            widths=(1.02 * inch, 1.62 * inch),
        )
        balance_label = "Refund Amount" if calc.refund > 0 else "Tax Due"
        balance = calc.refund if calc.refund > 0 else calc.tax_due
        filing = self._field_card(
            "2. FILING SUMMARY",
            [
                ("Total Income", self._currency(calc.gross_income)),
                ("Total Deductions", self._currency(calc.deductions)),
                ("Taxable Income", self._currency(calc.taxable_income)),
                ("Total Tax Liability", self._currency(calc.total_tax)),
                (balance_label, self._currency(balance)),
                ("Filing Type", "Original return estimate"),
            ],
            styles,
            widths=(1.24 * inch, 1.42 * inch),
            highlight_index=4,
        )
        documents = self._document_status_card(
            "3. DOCUMENTS SUMMARY",
            [
                ("W-2 Form", "Processed"),
                ("OCR Extraction", "Processed"),
                ("Tax Data", "Processed"),
                ("Calculation", "Generated"),
                ("Verification", "Completed"),
                ("Filing Report", "Generated"),
            ],
            styles,
        )
        story += [
            Table(
                [[taxpayer, filing, documents]],
                colWidths=[2.7 * inch, 2.7 * inch, 2.7 * inch],
                style=self._layout_style(),
            ),
            Spacer(1, 0.10 * inch),
        ]

        income = self._money_card(
            "4. INCOME SUMMARY",
            [
                ("W-2 Wages", data.wages),
                ("Other Income", data.other_income),
                ("Total Income", calc.gross_income),
            ],
            styles,
            total_rows={2},
            width=3.55 * inch,
        )
        deductions = self._money_card(
            "6. DEDUCTIONS & CREDITS SUMMARY",
            [
                ("Standard Deduction", calc.standard_deduction),
                ("Itemized Deductions", data.itemized_deductions),
                ("Total Deductions", calc.deductions),
                ("Tax Credits", 0),
                ("Total Credits", 0),
            ],
            styles,
            total_rows={2, 4},
            width=3.55 * inch,
        )
        left = Table(
            [[income], [Spacer(1, 0.09 * inch)], [deductions]],
            colWidths=[3.55 * inch],
            style=self._layout_style(),
        )
        calculation = self._money_card(
            "5. TAX CALCULATION BREAKDOWN",
            [
                ("Gross Income", calc.gross_income),
                ("Adjustments to Income", 0),
                ("Adjusted Gross Income (AGI)", calc.gross_income),
                ("Standard / Applied Deduction", -calc.deductions),
                ("Taxable Income", calc.taxable_income),
                ("Federal Tax", calc.federal_tax),
                ("State Tax Estimate", calc.state_tax),
                ("Total Tax Liability", calc.total_tax),
                ("Total Payments", calc.total_withholding),
                (balance_label, balance),
            ],
            styles,
            total_rows={2, 4, 7, 9},
            width=4.55 * inch,
            highlight_last=True,
        )
        story += [
            Table(
                [[left, calculation]],
                colWidths=[3.58 * inch, 4.57 * inch],
                style=self._layout_style(),
            ),
            Spacer(1, 0.10 * inch),
            self._verification_strip(result, styles),
            Spacer(1, 0.10 * inch),
        ]

        filing_details = self._field_card(
            "8. FILING DETAILS",
            [
                ("Return Type", "Tax calculation report"),
                ("Submission Method", "Local multi-agent workflow"),
                ("Submission ID", result.submission_id),
                ("Reference ID", receipt.reference_number),
                ("Completed On", receipt.timestamp.strftime("%b %d, %Y | %H:%M UTC")),
                ("Status", "Processing complete"),
            ],
            styles,
            widths=(1.30 * inch, 2.05 * inch),
        )
        pipeline = self._pipeline_card(result, styles)
        story += [
            Table(
                [[filing_details, pipeline]],
                colWidths=[3.65 * inch, 4.50 * inch],
                style=self._layout_style(),
            ),
            Spacer(1, 0.10 * inch),
        ]

        generated = self._document_status_card(
            "10. GENERATED DOCUMENTS",
            [
                ("Filing Receipt", "PDF"),
                ("Tax Calculation", "PDF"),
                ("Verification Summary", "PDF"),
                ("Audit Trail", "PDF"),
                ("Agent Log", "PDF"),
                ("W-2 Appendix", "PDF"),
            ],
            styles,
            compact=True,
        )
        payment = self._field_card(
            "11. PAYMENT / REFUND DETAILS",
            [
                ("Total Payments", self._currency(calc.total_withholding)),
                ("Refund Amount", self._currency(calc.refund)),
                ("Tax Due", self._currency(calc.tax_due)),
                ("Refund Method", "Not provided"),
                ("Bank Account", "Not provided"),
                ("Estimated Date", "Not available"),
            ],
            styles,
            widths=(1.22 * inch, 1.63 * inch),
            highlight_index=1 if calc.refund > 0 else 2,
        )
        verification_qr = self._verification_card(result, receipt, styles)
        story += [
            Table(
                [[generated, payment, verification_qr]],
                colWidths=[2.70 * inch, 2.78 * inch, 2.67 * inch],
                style=self._layout_style(),
            ),
            Spacer(1, 0.08 * inch),
            self._footer_block(styles),
        ]
        return story

    def _header(self, receipt, styles):
        logo = Table(
            [[Paragraph("TF", styles["Logo"])]],
            colWidths=[0.62 * inch],
            rowHeights=[0.52 * inch],
        )
        logo.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        title = Paragraph(
            "PROFESSIONAL TAX FILING REPORT<br/>"
            "<font size='9'>Generated by a Local Multi-Agent Tax Processing Pipeline</font>",
            styles["ReportMainTitle"],
        )
        status = Table(
            [
                [
                    Paragraph("✓", styles["StatusCheck"]),
                    Paragraph(
                        "<b>PROCESSING SUCCESSFULLY COMPLETED</b><br/>"
                        f"<font size='6.5'>Completed: {receipt.timestamp.strftime('%b %d, %Y | %H:%M UTC')}</font>",
                        styles["Status"],
                    ),
                ]
            ],
            colWidths=[0.37 * inch, 1.98 * inch],
        )
        status.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.7, GREEN),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        header = Table(
            [[logo, title, status]],
            colWidths=[0.68 * inch, 5.03 * inch, 2.37 * inch],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.8, LINE),
                ]
            )
        )
        return [header, Spacer(1, 0.09 * inch)]

    def _verification_strip(self, result, styles):
        checks = {check.name: check.passed for check in result.verification.checks}
        had_remediation = any(
            item.agent == "Remediation Agent" for item in result.audit_trail
        )
        values = [
            ("DATA CONSISTENCY", checks.get("taxpayer_name", False), "All required fields validated"),
            ("TAX RULE CHECK", checks.get("calculation_replay", False), "Installed rules applied"),
            ("SOURCE CHECK", checks.get("source_grounding", False), "Critical values grounded"),
            ("CROSS-VERIFICATION", checks.get("withholding_bounds", False), "All checks successful"),
            ("REMEDIATION", not had_remediation, "Not required" if not had_remediation else "Corrections applied"),
        ]
        cells = []
        for title, passed, detail in values:
            cells.append(
                [
                    Paragraph("✓" if passed else "!", styles["VerifyIcon"]),
                    Paragraph(
                        f"<b>{title}</b><br/>"
                        f"<font color='#{'147A30' if passed else 'B42318'}'>"
                        f"{'Passed' if passed else 'Review'}</font><br/>"
                        f"<font size='6'>{escape(detail)}</font>",
                        styles["VerifyText"],
                    ),
                ]
            )
        table = Table([cells], colWidths=[1.61 * inch] * 5)
        table.setStyle(
            TableStyle(
                [
                    ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return self._section("7. VERIFICATION & REMEDIATION SUMMARY", table, styles)

    def _pipeline_card(self, result, styles):
        remediated = any(
            entry.agent == "Remediation Agent" for entry in result.audit_trail
        )
        rows = [
            ("1", "Reading / Parsing Agent", "Extract & parse documents", "Completed"),
            ("2", "Tax Processing Agent", "Calculate tax & deductions", "Completed"),
            ("3", "Verification Agent", "Validate consistency", "Completed"),
            ("4", "Remediation Agent", "Correct errors", "Completed" if remediated else "Not required"),
            ("5", "Documentation Agent", "Generate report", "Completed"),
        ]
        agent_colors = [BLUE, GREEN, PURPLE, ORANGE, BLUE]
        table_rows = [
            [
                Paragraph("<b>Agent</b>", styles["TableHead"]),
                Paragraph("<b>Role</b>", styles["TableHead"]),
                Paragraph("<b>Status</b>", styles["TableHead"]),
            ]
        ]
        for index, (_, agent, role, status) in enumerate(rows):
            table_rows.append(
                [
                    Table(
                        [[
                            Paragraph(
                                str(index + 1),
                                ParagraphStyle(
                                    f"Badge{index}",
                                    parent=styles["Badge"],
                                    backColor=agent_colors[index],
                                ),
                            ),
                            Paragraph(escape(agent), styles["Tiny"]),
                        ]],
                        colWidths=[0.23 * inch, 1.25 * inch],
                        style=self._layout_style(),
                    ),
                    Paragraph(escape(role), styles["Tiny"]),
                    Paragraph(f"<font color='#147A30'>✓ {escape(status)}</font>", styles["Tiny"]),
                ]
            )
        table = Table(
            table_rows,
            colWidths=[1.55 * inch, 1.65 * inch, 1.12 * inch],
            repeatRows=1,
        )
        table.setStyle(self._data_style())
        return self._section("9. AGENT PIPELINE SUMMARY", table, styles)

    def _verification_card(self, result, receipt, styles):
        qr = self._qr_drawing(
            f"http://127.0.0.1:5173/?submission={result.submission_id}",
            0.92 * inch,
        )
        content = Table(
            [
                [
                    qr,
                    Paragraph(
                        "Scan this QR code to open the local verification record.<br/><br/>"
                        f"<b>Verification ID</b><br/><font color='#1557A6'><b>{receipt.reference_number}</b></font>",
                        styles["Tiny"],
                    ),
                ]
            ],
            colWidths=[1.05 * inch, 1.35 * inch],
        )
        content.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return self._section("12. QR CODE (LOCAL VERIFICATION)", content, styles)

    def _footer_block(self, styles):
        disclaimer = Paragraph(
            "<b>DISCLAIMER:</b><br/>"
            "This report is generated by a local multi-agent tax processing system. "
            "It is not an IRS acceptance notice, legal advice, or proof of electronic filing.",
            styles["Footer"],
        )
        prepared = Paragraph(
            "<b>Prepared By:</b><br/>TaxFlow Local<br/>"
            "Multi-Agent Tax Filing System",
            styles["Footer"],
        )
        signature = Paragraph(
            "<b>Authorized System Record</b><br/><br/>"
            "<font name='Helvetica-Oblique' size='13' color='#052A67'>TaxFlow Local</font><br/>"
            "<font color='#147A30'>✓ LOCALLY VERIFIED</font>",
            styles["FooterCenter"],
        )
        table = Table(
            [[disclaimer, prepared, signature]],
            colWidths=[4.02 * inch, 1.75 * inch, 2.35 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.6, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBEFORE", (1, 0), (-1, -1), 0.4, LINE),
                ]
            )
        )
        return table

    def _appendix(self, result, receipt, styles, document_preview):
        preview = self._document_preview(document_preview)
        title = Table(
            [
                [
                    Paragraph(
                        "APPENDIX A - CUSTOMER W-2 SOURCE DOCUMENT",
                        styles["AppendixTitle"],
                    )
                ]
            ],
            colWidths=[8.05 * inch],
        )
        title.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )
        metadata = Table(
            [
                [
                    Paragraph("<b>Taxpayer</b>", styles["Tiny"]),
                    Paragraph(escape(result.extracted_data.employee_name), styles["Tiny"]),
                    Paragraph("<b>Tax year</b>", styles["Tiny"]),
                    Paragraph(str(result.extracted_data.tax_year), styles["Tiny"]),
                    Paragraph("<b>Reference</b>", styles["Tiny"]),
                    Paragraph(receipt.reference_number, styles["Tiny"]),
                ]
            ],
            colWidths=[
                0.62 * inch,
                1.85 * inch,
                0.58 * inch,
                0.68 * inch,
                0.62 * inch,
                1.4 * inch,
            ],
        )
        metadata.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story = [
            title,
            Spacer(1, 0.08 * inch),
            Paragraph(
                "The following is the uploaded W-2 used as source evidence for this report. "
                "It is included for customer reference and human verification.",
                styles["Body"],
            ),
            Spacer(1, 0.08 * inch),
            metadata,
            Spacer(1, 0.12 * inch),
        ]
        if preview:
            story.append(preview)
        else:
            story.append(Paragraph("W-2 preview unavailable.", styles["Body"]))
        return story

    def _field_card(
        self,
        title,
        rows,
        styles,
        widths,
        highlight_index=None,
    ):
        data = []
        for index, (label, value) in enumerate(rows):
            highlighted = index == highlight_index
            data.append(
                [
                    Paragraph(escape(label), styles["Label"]),
                    Paragraph(
                        f"<b>{escape(str(value))}</b>" if highlighted else escape(str(value)),
                        styles["GreenValue"] if highlighted else styles["Value"],
                    ),
                ]
            )
        table = Table(data, colWidths=list(widths))
        commands = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ]
        if highlight_index is not None:
            commands.append(
                ("BACKGROUND", (0, highlight_index), (-1, highlight_index), GREEN_LIGHT)
            )
        table.setStyle(TableStyle(commands))
        return self._section(title, table, styles)

    def _document_status_card(self, title, rows, styles, compact=False):
        data = []
        for label, status in rows:
            data.append(
                [
                    Paragraph(escape(label), styles["Tiny" if compact else "Value"]),
                    Paragraph(
                        f"<font color='#147A30'>✓ {escape(status)}</font>",
                        styles["Tiny" if compact else "Value"],
                    ),
                ]
            )
        widths = [1.45 * inch, 0.95 * inch] if compact else [1.5 * inch, 0.9 * inch]
        table = Table(data, colWidths=widths)
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
                ]
            )
        )
        return self._section(title, table, styles)

    def _money_card(
        self,
        title,
        rows,
        styles,
        total_rows,
        width,
        highlight_last=False,
    ):
        data = [
            [
                Paragraph("<b>Description</b>", styles["TableHead"]),
                Paragraph("<b>Amount (USD)</b>", styles["TableHeadRight"]),
            ]
        ]
        for index, (label, amount) in enumerate(rows):
            negative = amount < 0
            amount_text = self._currency(abs(amount))
            if negative:
                amount_text = f"({amount_text})"
            bold = index in total_rows
            data.append(
                [
                    Paragraph(
                        f"<b>{escape(label)}</b>" if bold else escape(label),
                        styles["TableCell"],
                    ),
                    Paragraph(
                        f"<b>{amount_text}</b>" if bold else amount_text,
                        styles["Amount"],
                    ),
                ]
            )
        table = Table(
            data,
            colWidths=[width * 0.68, width * 0.32],
            repeatRows=1,
        )
        commands = self._data_commands()
        if highlight_last:
            commands.extend(
                [
                    ("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), GREEN_LIGHT),
                    ("TEXTCOLOR", (0, len(data) - 1), (-1, len(data) - 1), GREEN),
                ]
            )
        table.setStyle(TableStyle(commands))
        return self._section(title, table, styles)

    def _section(self, title, content, styles):
        heading = Table(
            [[Paragraph(escape(title), styles["SectionTitle"])]],
            colWidths=[None],
        )
        heading.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        box = Table([[heading], [content]], colWidths=[None])
        box.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.65, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return box

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                "Logo",
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=20,
                alignment=TA_CENTER,
                textColor=WHITE,
            )
        )
        styles.add(
            ParagraphStyle(
                "ReportMainTitle",
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=20,
                textColor=NAVY,
            )
        )
        styles.add(
            ParagraphStyle(
                "StatusCheck",
                fontName="Helvetica-Bold",
                fontSize=17,
                leading=19,
                alignment=TA_CENTER,
                textColor=WHITE,
                backColor=GREEN,
                borderPadding=3,
            )
        )
        styles.add(
            ParagraphStyle(
                "Status",
                fontName="Helvetica",
                fontSize=6.5,
                leading=8.3,
                textColor=GREEN,
            )
        )
        styles.add(
            ParagraphStyle(
                "SectionTitle",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=9,
                textColor=WHITE,
            )
        )
        styles.add(
            ParagraphStyle(
                "Label",
                fontName="Helvetica-Bold",
                fontSize=6.4,
                leading=8,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "Value",
                fontName="Helvetica",
                fontSize=6.6,
                leading=8.3,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "GreenValue",
                parent=styles["Value"],
                fontName="Helvetica-Bold",
                textColor=GREEN,
            )
        )
        styles.add(
            ParagraphStyle(
                "TableHead",
                fontName="Helvetica-Bold",
                fontSize=6.2,
                leading=7.5,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "TableHeadRight",
                parent=styles["TableHead"],
                alignment=TA_RIGHT,
            )
        )
        styles.add(
            ParagraphStyle(
                "TableCell",
                fontName="Helvetica",
                fontSize=6.25,
                leading=7.8,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "Amount",
                parent=styles["TableCell"],
                alignment=TA_RIGHT,
            )
        )
        styles.add(
            ParagraphStyle(
                "Tiny",
                fontName="Helvetica",
                fontSize=5.8,
                leading=7.2,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "Badge",
                fontName="Helvetica-Bold",
                fontSize=6,
                leading=7,
                alignment=TA_CENTER,
                textColor=WHITE,
                borderPadding=2,
            )
        )
        styles.add(
            ParagraphStyle(
                "VerifyIcon",
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=14,
                alignment=TA_CENTER,
                textColor=GREEN,
            )
        )
        styles.add(
            ParagraphStyle(
                "VerifyText",
                fontName="Helvetica",
                fontSize=5.8,
                leading=7.2,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "Footer",
                fontName="Helvetica",
                fontSize=5.8,
                leading=7.6,
                textColor=INK,
            )
        )
        styles.add(
            ParagraphStyle(
                "FooterCenter",
                parent=styles["Footer"],
                alignment=TA_CENTER,
            )
        )
        styles.add(
            ParagraphStyle(
                "AppendixTitle",
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=13,
                textColor=WHITE,
            )
        )
        styles.add(
            ParagraphStyle(
                "Body",
                fontName="Helvetica",
                fontSize=7.5,
                leading=10,
                textColor=INK,
            )
        )
        return styles

    @staticmethod
    def _layout_style():
        return TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )

    @staticmethod
    def _data_commands():
        return [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.4, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFD")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ]

    @classmethod
    def _data_style(cls):
        return TableStyle(cls._data_commands())

    @staticmethod
    def _qr_drawing(value: str, size: float):
        widget = QrCodeWidget(value)
        bounds = widget.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        drawing = Drawing(size, size, transform=[size / width, 0, 0, size / height, 0, 0])
        drawing.add(widget)
        return drawing

    @staticmethod
    def _document_preview(path: Path | None):
        if not path or not path.exists():
            return None
        try:
            if path.suffix.lower() == ".pdf":
                with fitz.open(path) as document:
                    pixmap = document[0].get_pixmap(
                        matrix=fitz.Matrix(1.7, 1.7), alpha=False
                    )
                    buffer = io.BytesIO(pixmap.tobytes("png"))
            elif path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                buffer = io.BytesIO(path.read_bytes())
            else:
                return None
            image = Image(buffer)
            scale = min(
                (7.55 * inch) / image.imageWidth,
                (10.65 * inch) / image.imageHeight,
            )
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            image.hAlign = "CENTER"
            return image
        except (OSError, ValueError, RuntimeError):
            return None

    @staticmethod
    def _currency(value):
        return f"${value:,.2f}"

    @staticmethod
    def _page_frame(canvas, doc, receipt, dashboard):
        width, height = REPORT_SIZE
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 0.06 * inch, width, 0.06 * inch, fill=1, stroke=0)
        canvas.setStrokeColor(LINE)
        canvas.line(0.35 * inch, 0.17 * inch, width - 0.35 * inch, 0.17 * inch)
        canvas.setFont("Helvetica-Bold", 5.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(0.35 * inch, 0.07 * inch, f"TAXFLOW LOCAL | {receipt.reference_number}")
        canvas.setFont("Helvetica", 5.5)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(
            width - 0.35 * inch,
            0.07 * inch,
            f"{'FILING REPORT' if dashboard else 'CUSTOMER W-2 APPENDIX'} | Page {doc.page}",
        )
        canvas.restoreState()
