from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FilingStatus(StrEnum):
    SINGLE = "single"
    MARRIED_JOINTLY = "married_filing_jointly"
    MARRIED_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class WorkflowStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    CALCULATING = "calculating"
    VERIFYING = "verifying"
    REMEDIATING = "remediating"
    COMPLETED = "completed"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"


class SourceEvidence(BaseModel):
    field: str
    page: int = 1
    raw_text: str = ""
    source: str = "ocr"
    confidence: float = Field(default=0.0, ge=0, le=1)


class TaxpayerData(BaseModel):
    employee_name: str = ""
    employer_name: str = ""
    filing_status: FilingStatus = FilingStatus.SINGLE
    tax_year: int = 2025
    wages: Decimal = Decimal("0")
    federal_tax_withheld: Decimal = Decimal("0")
    state_tax_withheld: Decimal = Decimal("0")
    other_income: Decimal = Decimal("0")
    itemized_deductions: Decimal = Decimal("0")
    state_tax_rate: Decimal = Decimal("0.05")
    state: str = ""
    evidence: list[SourceEvidence] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator(
        "wages",
        "federal_tax_withheld",
        "state_tax_withheld",
        "other_income",
        "itemized_deductions",
        "state_tax_rate",
        mode="before",
    )
    @classmethod
    def normalize_decimal(cls, value: Any) -> Decimal:
        if value in (None, ""):
            return Decimal("0")
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").strip()
        return Decimal(str(value))


class TaxCalculation(BaseModel):
    gross_income: Decimal
    standard_deduction: Decimal
    deductions: Decimal
    taxable_income: Decimal
    federal_tax: Decimal
    state_tax: Decimal
    total_tax: Decimal
    total_withholding: Decimal
    refund: Decimal
    tax_due: Decimal
    trace: list[str] = Field(default_factory=list)


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    message: str
    weight: float = 1.0


class VerificationResult(BaseModel):
    valid: bool
    confidence_score: float = Field(ge=0, le=1)
    checks: list[VerificationCheck]
    hallucination_flags: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AuditEntry(BaseModel):
    agent: str
    action: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FilingReceipt(BaseModel):
    submission_id: str
    reference_number: str
    timestamp: datetime
    filing_status: str


class SubmissionResult(BaseModel):
    submission_id: str
    status: WorkflowStatus
    original_filename: str
    extracted_data: TaxpayerData | None = None
    calculation: TaxCalculation | None = None
    verification: VerificationResult | None = None
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    receipt: FilingReceipt | None = None
    report_url: str | None = None
    error: str | None = None
