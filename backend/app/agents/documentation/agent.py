from datetime import datetime, timezone
from pathlib import Path

from app.schemas import AuditEntry, FilingReceipt, SubmissionResult
from app.services.pdf.report import PDFReportService


class DocumentationAgent:
    name = "Documentation Agent"

    def __init__(self, reports: PDFReportService):
        self.reports = reports

    def run(
        self,
        result: SubmissionResult,
        output: Path,
        preview: Path | None = None,
    ) -> tuple[FilingReceipt, Path, AuditEntry]:
        if not result.verification or not result.verification.valid:
            raise ValueError("Cannot generate final report before verification")
        timestamp = datetime.now(timezone.utc)
        receipt = FilingReceipt(
            submission_id=result.submission_id,
            reference_number=f"TX{result.extracted_data.tax_year}-{result.submission_id[:8].upper()}",
            timestamp=timestamp,
            filing_status="ready_for_filing",
        )
        path = self.reports.generate(result, receipt, output, preview)
        return receipt, path, AuditEntry(
            agent=self.name,
            action="generate_pdf",
            reason="Create verified filing report and receipt",
            details={"path": str(path), "reference": receipt.reference_number},
        )
