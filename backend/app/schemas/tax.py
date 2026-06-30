from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FilingStatus(StrEnum):
    SINGLE = "single"
    MARRIED_JOINTLY = "married_filing_jointly"
    MARRIED_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"


class WorkflowStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSING = "parsing"
    CALCULATING = "calculating"
    VERIFYING = "verifying"
    REMEDIATING = "remediating"
    COMPLETED = "completed"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"


def mask_ssn(value: str) -> str:
    """Return an SSN with all but the last four digits masked."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 4:
        return "***-**-****" if digits else ""
    return f"***-**-{digits[-4:]}"


class SourceEvidence(BaseModel):
    field: str
    page: int = 1
    raw_text: str = ""
    source: str = "ocr"
    confidence: float = Field(default=0.0, ge=0, le=1)


class W2(BaseModel):
    """A single Form W-2. Multiple may be attached to one taxpayer."""

    employer_name: str = ""
    employer_ein: str = ""
    box1_wages: Decimal = Decimal("0")
    box2_federal_withheld: Decimal = Decimal("0")
    box3_ss_wages: Decimal = Decimal("0")
    box4_ss_withheld: Decimal = Decimal("0")
    box5_medicare_wages: Decimal = Decimal("0")
    box6_medicare_withheld: Decimal = Decimal("0")
    box15_state: str = ""  # Employer's state (USPS code)
    box17_state_withheld: Decimal = Decimal("0")

    @field_validator(
        "box1_wages",
        "box2_federal_withheld",
        "box3_ss_wages",
        "box4_ss_withheld",
        "box5_medicare_wages",
        "box6_medicare_withheld",
        "box17_state_withheld",
        mode="before",
    )
    @classmethod
    def _decimal(cls, value: Any) -> Decimal:
        return _to_decimal(value)

    @field_validator("box15_state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        return normalize_state(value)


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
    return Decimal(str(value))


_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
_STATE_CODES = set(_STATE_NAMES)
_STATE_NAME_TO_CODE = {name.lower(): code for code, name in _STATE_NAMES.items()}


def normalize_state(value: Any) -> str:
    """Normalize a free-text state to a USPS code (e.g. "california" -> "CA").

    Returns "" for empty/None. A recognized two-letter code or full name maps to
    its canonical code; anything else is upper-cased and passed through (so it
    simply won't match a rule pack -- a safe no-op rather than a wrong state).
    """
    if not value or not isinstance(value, str):
        return ""
    v = value.strip()
    if not v:
        return ""
    if len(v) == 2 and v.upper() in _STATE_CODES:
        return v.upper()
    key = v.lower().replace(".", "").strip()
    if key in _STATE_NAME_TO_CODE:
        return _STATE_NAME_TO_CODE[key]
    compact = re.sub(r"[^a-z]", "", key)
    if len(compact) == 2 and compact.upper() in _STATE_CODES:
        return compact.upper()  # e.g. "D.C." -> "DC"
    return v.upper()


class TaxpayerData(BaseModel):
    # Identity
    employee_name: str = ""
    spouse_name: str = ""
    ssn: str = ""
    employer_name: str = ""
    filing_status: FilingStatus = FilingStatus.SINGLE
    tax_year: int = 2025

    # Age / blindness (drive the additional standard deduction)
    age_65_plus: bool = False
    spouse_65_plus: bool = False
    blind: bool = False
    spouse_blind: bool = False
    # Exact ages (0 = unknown) for finer state age thresholds (e.g. NY pension
    # exclusion at 59.5, NJ retirement exclusion at 62). Federal still uses the
    # 65+ booleans above; these only refine state rule packs.
    age: int = 0
    spouse_age: int = 0
    # Date of birth (optional). When present, state packs use exact age at the
    # tax year-end (so the 59.5 / "turns 62 this year" boundaries are precise);
    # otherwise they fall back to ``age`` then the 65+ booleans.
    birth_date: date | None = None
    spouse_birth_date: date | None = None

    # Dependents
    qualifying_children: int = 0  # CTC-eligible
    other_dependents: int = 0  # Credit for Other Dependents

    # Wage income (aggregated across W-2s)
    w2s: list[W2] = Field(default_factory=list)
    wages: Decimal = Decimal("0")
    federal_tax_withheld: Decimal = Decimal("0")
    state_tax_withheld: Decimal = Decimal("0")
    ss_wages: Decimal = Decimal("0")
    ss_tax_withheld: Decimal = Decimal("0")
    medicare_wages: Decimal = Decimal("0")
    medicare_tax_withheld: Decimal = Decimal("0")
    employer_count: int = 0

    # Other income
    taxable_interest: Decimal = Decimal("0")
    tax_exempt_interest: Decimal = Decimal("0")
    ordinary_dividends: Decimal = Decimal("0")
    qualified_dividends: Decimal = Decimal("0")
    long_term_capital_gain: Decimal = Decimal("0")
    short_term_capital_gain: Decimal = Decimal("0")
    capital_loss_carryover: Decimal = Decimal("0")  # prior-year loss (positive)
    self_employment_income: Decimal = Decimal("0")  # net profit (Sch C)
    partnership_income: Decimal = Decimal("0")  # K-1 ordinary business income
    taxable_pension_ira: Decimal = Decimal("0")  # 1099-R box 2a
    social_security_benefits: Decimal = Decimal("0")  # SSA-1099 (gross)
    other_income: Decimal = Decimal("0")

    # Adjustments / deductions / payments
    adjustments: Decimal = Decimal("0")  # above-the-line (Sch 1 Part II)
    itemized_deductions: Decimal = Decimal("0")  # pre-computed total (fallback)
    # Schedule A line items (used to compute itemized + AMT SALT add-back).
    salt_paid: Decimal = Decimal("0")  # state/local taxes (before $10k cap)
    mortgage_interest: Decimal = Decimal("0")
    medical_expenses: Decimal = Decimal("0")
    charitable_contributions: Decimal = Decimal("0")
    estimated_payments: Decimal = Decimal("0")

    # Credits & AMT inputs
    qualified_tuition: Decimal = Decimal("0")  # education credits
    aotc_students: int = 0  # students eligible for American Opportunity Credit
    retirement_contributions: Decimal = Decimal("0")  # Saver's Credit
    amt_preference_items: Decimal = Decimal("0")  # ISO bargain element, PAB, etc.

    # State. ``state`` (USPS code) selects an installed rule pack in
    # ``app.state_rules``; absent a pack, ``state_tax_rate`` is the flat-rate
    # fallback (default 0 = no state tax). See app.state_rules for the packs.
    state_tax_rate: Decimal = Decimal("0")
    state: str = ""

    evidence: list[SourceEvidence] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator(
        "wages",
        "federal_tax_withheld",
        "state_tax_withheld",
        "ss_wages",
        "ss_tax_withheld",
        "medicare_wages",
        "medicare_tax_withheld",
        "taxable_interest",
        "tax_exempt_interest",
        "ordinary_dividends",
        "qualified_dividends",
        "long_term_capital_gain",
        "short_term_capital_gain",
        "capital_loss_carryover",
        "self_employment_income",
        "partnership_income",
        "taxable_pension_ira",
        "social_security_benefits",
        "other_income",
        "adjustments",
        "itemized_deductions",
        "salt_paid",
        "mortgage_interest",
        "medical_expenses",
        "charitable_contributions",
        "estimated_payments",
        "qualified_tuition",
        "retirement_contributions",
        "amt_preference_items",
        "state_tax_rate",
        mode="before",
    )
    @classmethod
    def normalize_decimal(cls, value: Any) -> Decimal:
        return _to_decimal(value)

    @field_validator("state", mode="before")
    @classmethod
    def _normalize_state(cls, value: Any) -> str:
        return normalize_state(value)

    @property
    def masked_ssn(self) -> str:
        return mask_ssn(self.ssn)

    def aggregate_w2s(self) -> None:
        """Fold the ``w2s`` list into the scalar wage/withholding totals.

        Only runs when W-2 line items are present, so single-document
        extraction that populates the scalar fields directly is unaffected.
        """
        if not self.w2s:
            return
        self.wages = sum((w.box1_wages for w in self.w2s), Decimal("0"))
        self.federal_tax_withheld = sum(
            (w.box2_federal_withheld for w in self.w2s), Decimal("0")
        )
        self.ss_wages = sum((w.box3_ss_wages for w in self.w2s), Decimal("0"))
        self.ss_tax_withheld = sum(
            (w.box4_ss_withheld for w in self.w2s), Decimal("0")
        )
        self.medicare_wages = sum(
            (w.box5_medicare_wages for w in self.w2s), Decimal("0")
        )
        self.medicare_tax_withheld = sum(
            (w.box6_medicare_withheld for w in self.w2s), Decimal("0")
        )
        self.state_tax_withheld = sum(
            (w.box17_state_withheld for w in self.w2s), Decimal("0")
        )
        # Derive the resident/work state from the W-2s when not already set.
        # The primary state is the one with the most state tax withheld.
        if not self.state:
            with_state = [w for w in self.w2s if w.box15_state]
            if with_state:
                self.state = max(
                    with_state, key=lambda w: w.box17_state_withheld
                ).box15_state
        self.employer_count = len(self.w2s)


class TaxCalculation(BaseModel):
    # --- Income / AGI ---
    gross_income: Decimal  # total income (kept name for report/UI compat)
    total_income: Decimal = Decimal("0")
    taxable_social_security: Decimal = Decimal("0")
    capital_loss_carryforward: Decimal = Decimal("0")
    adjustments: Decimal = Decimal("0")
    adjusted_gross_income: Decimal = Decimal("0")

    # --- Deductions ---
    standard_deduction: Decimal
    additional_standard_deduction: Decimal = Decimal("0")
    senior_deduction: Decimal = Decimal("0")
    deductions: Decimal  # the amount actually used (max of std-stack vs itemized)
    qbi_deduction: Decimal = Decimal("0")  # Form 8995 (simplified)
    taxable_income: Decimal

    # --- Income tax (ordinary + preferential) ---
    ordinary_taxable_income: Decimal = Decimal("0")
    ordinary_tax: Decimal = Decimal("0")
    preferential_tax: Decimal = Decimal("0")  # qualified div + net LTCG
    income_tax_before_credits: Decimal = Decimal("0")
    tax_table_used: bool = False

    # --- Credits (nonrefundable) ---
    child_tax_credit: Decimal = Decimal("0")
    other_dependent_credit: Decimal = Decimal("0")
    education_credits: Decimal = Decimal("0")  # nonrefundable AOTC + LLC
    savers_credit: Decimal = Decimal("0")
    nonrefundable_credits: Decimal = Decimal("0")

    # --- Other federal taxes ---
    self_employment_tax: Decimal = Decimal("0")
    additional_medicare_tax: Decimal = Decimal("0")
    net_investment_income_tax: Decimal = Decimal("0")
    alternative_minimum_tax: Decimal = Decimal("0")
    other_taxes: Decimal = Decimal("0")

    # --- Totals ---
    federal_tax: Decimal  # total federal tax after credits + other taxes
    state_tax: Decimal
    total_tax: Decimal  # federal + state (kept name for report/UI compat)

    # --- Payments ---
    total_withholding: Decimal  # federal + state withholding (report/UI compat)
    estimated_payments: Decimal = Decimal("0")
    excess_ss_credit: Decimal = Decimal("0")
    refundable_child_tax_credit: Decimal = Decimal("0")
    earned_income_credit: Decimal = Decimal("0")
    refundable_education_credit: Decimal = Decimal("0")  # refundable AOTC
    total_payments: Decimal = Decimal("0")

    # --- Result (federal) ---
    refund: Decimal
    tax_due: Decimal
    # State shown separately (only meaningful when a state rate is supplied).
    state_refund: Decimal = Decimal("0")
    state_balance_due: Decimal = Decimal("0")

    params_verified: bool = True
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
    correctness_ok: bool = True
    completeness_ok: bool = True
    requires_reextraction: bool = False


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
