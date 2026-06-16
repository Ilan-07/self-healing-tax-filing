from datetime import datetime, timezone
from pathlib import Path

from app.schemas import AuditEntry, FilingReceipt, SubmissionResult
from app.services.efile import EFileBackend, PdfSelfFileBackend
from app.services.pdf.professional_report import ProfessionalReportService


class DocumentationAgent:
    name = "Documentation Agent"

    def __init__(
        self,
        reports: ProfessionalReportService,
        efile: EFileBackend | None = None,
    ):
        self.reports = reports
        self.efile = efile or PdfSelfFileBackend()

    def run(
        self,
        result: SubmissionResult,
        output: Path,
        preview: Path | None = None,
    ) -> tuple[FilingReceipt, Path, AuditEntry]:
        if not result.verification or not result.verification.valid:
            raise ValueError("Cannot generate final report before verification")
        timestamp = datetime.now(timezone.utc)
        ack = self.efile.submit(result)
        year = result.extracted_data.tax_year if result.extracted_data else 0
        receipt = FilingReceipt(
            submission_id=result.submission_id,
            reference_number=(
                ack.acknowledgement_id
                or f"TX{year}-{result.submission_id[:8].upper()}"
            ),
            timestamp=timestamp,
            filing_status=ack.status,
        )
        path = self.reports.generate(result, receipt, output)
        return receipt, path, AuditEntry(
            agent=self.name,
            action="generate_pdf",
            reason="Create verified return, route to e-file boundary, issue receipt",
            details={
                "path": str(path),
                "reference": receipt.reference_number,
                "efile_channel": ack.channel,
                "efile_status": ack.status,
                "accepted": ack.accepted,
                "reject_codes": ack.reject_codes,
            },
        )
