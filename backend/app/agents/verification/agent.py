"""Verification agent.

Emits two independent verdicts:
  * correctness_ok  -- the return is internally consistent and the arithmetic is
    sound (W-2 invariants, source grounding for every monetary field, and a
    deterministic recomputation from the raw extracted inputs).
  * completeness_ok -- no income appears to be missing (transcript reconciliation
    when available, otherwise coverage heuristics).

A submission is VALID only when both hold, confidence clears the threshold, and
there are no hard violations.
"""

from __future__ import annotations

from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.agents.verification.completeness import check_completeness
from app.schemas import (
    AuditEntry,
    TaxCalculation,
    TaxpayerData,
    VerificationCheck,
    VerificationResult,
)


# Every monetary field that affects the result must be grounded in evidence.
MONETARY_FIELDS = (
    "wages",
    "federal_tax_withheld",
    "state_tax_withheld",
    "taxable_interest",
    "ordinary_dividends",
    "qualified_dividends",
    "long_term_capital_gain",
    "short_term_capital_gain",
    "self_employment_income",
    "other_income",
    "itemized_deductions",
)
CRITICAL_FIELDS = {"wages", "federal_tax_withheld"}
# W-2 invariant tolerance: 2% of the expected amount or $2, whichever is larger.
INVARIANT_REL = Decimal("0.02")
INVARIANT_ABS = Decimal("2")


class VerificationAgent:
    name = "Verification Agent"

    def __init__(self, calculator: TaxCalculator, threshold: float):
        self.calculator = calculator
        self.threshold = threshold

    def run(
        self,
        data: TaxpayerData,
        calculation: TaxCalculation,
        transcript: dict[str, object] | None = None,
    ) -> tuple[VerificationResult, AuditEntry]:
        checks: list[VerificationCheck] = []

        self._check(
            checks, "taxpayer_name", bool(data.employee_name.strip()),
            "Taxpayer name is present", "Taxpayer name is missing", 1.5,
        )
        self._check(
            checks, "taxpayer_ssn", _has_ssn(data.ssn),
            "Taxpayer SSN is present", "Taxpayer SSN is missing/invalid", 1.5,
        )
        self._check(
            checks, "income", _total_income(data) > 0,
            "Positive income found", "No income captured", 2,
        )
        self._check(
            checks, "withholding_bounds",
            data.federal_tax_withheld <= data.wages + data.self_employment_income
            and data.state_tax_withheld <= data.wages,
            "Withholding within income bounds",
            "A withholding value exceeds income", 2,
        )

        # --- W-2 statutory invariants (a genuine independent cross-check) ---
        for label, base, withheld, rate in (
            ("social_security", data.ss_wages, data.ss_tax_withheld, Decimal("0.062")),
            ("medicare", data.medicare_wages, data.medicare_tax_withheld, Decimal("0.0145")),
        ):
            if base > 0 and withheld > 0:
                expected = base * rate
                tol = max(INVARIANT_ABS, expected * INVARIANT_REL)
                self._check(
                    checks, f"w2_{label}_invariant",
                    abs(withheld - expected) <= tol,
                    f"W-2 {label} withholding matches {rate:.2%} of wages",
                    f"W-2 {label} withholding {withheld} != ~{expected:.0f}", 1.5,
                )

        # A real W-2 with box-1 wages always reports Social Security & Medicare
        # wages (boxes 3 & 5). Their absence signals an incomplete extraction
        # (e.g. a noisy scan), which must not pass silently.
        if data.wages > 0:
            self._check(
                checks, "w2_complete",
                data.ss_wages > 0 and data.medicare_wages > 0,
                "W-2 Social Security & Medicare wage boxes present",
                "W-2 appears incompletely extracted (missing SS/Medicare wages)",
                2,
            )

        # --- Deterministic recomputation from the RAW extracted inputs ---
        recalculated = self.calculator.calculate(data)
        arithmetic_ok = recalculated == calculation
        self._check(
            checks, "calculation_replay", arithmetic_ok,
            "Independent recomputation from raw inputs matched",
            "Stored calculation does not match a fresh recomputation", 3,
        )

        # --- Source grounding for every monetary field ---
        supported = {item.field for item in data.evidence}
        unsupported = [
            f for f in MONETARY_FIELDS
            if Decimal(getattr(data, f)) != Decimal("0") and f not in supported
        ]
        self._check(
            checks, "source_grounding", not unsupported,
            "All monetary values have source evidence",
            f"Ungrounded monetary fields: {', '.join(unsupported)}", 3,
        )
        critical_unsupported = [f for f in unsupported if f in CRITICAL_FIELDS]

        # --- Params provenance ---
        self._check(
            checks, "params_verified", calculation.params_verified,
            "Tax parameters are marked verified",
            "Tax parameters are not yet verified against IRS sources", 0.5,
        )

        # --- Completeness (independent verdict) ---
        completeness = check_completeness(data, transcript)
        self._check(
            checks, "completeness", completeness.ok,
            "No missing income detected",
            "; ".join(completeness.issues) or "Income may be incomplete", 2,
        )

        # --- Confidence ---
        evidence_scores = [
            v for k, v in data.field_confidence.items() if k in supported
        ]
        extraction_confidence = (
            sum(evidence_scores) / len(evidence_scores)
            if evidence_scores
            else 0.35
        )
        weighted_pass = sum(c.weight for c in checks if c.passed)
        total_weight = sum(c.weight for c in checks)
        rule_score = weighted_pass / total_weight if total_weight else 0
        confidence = round(0.8 * rule_score + 0.2 * extraction_confidence, 4)

        # correctness excludes the separately-reported completeness verdict and
        # the advisory params-provenance check (which only lowers confidence).
        soft = {"completeness", "params_verified"}
        correctness_ok = all(c.passed for c in checks if c.name not in soft)
        errors = [c.message for c in checks if not c.passed]
        if confidence < self.threshold:
            errors.append(
                f"Confidence {confidence:.1%} is below {self.threshold:.1%}"
            )

        result = VerificationResult(
            valid=(
                correctness_ok
                and completeness.ok
                and confidence >= self.threshold
            ),
            confidence_score=confidence,
            checks=checks,
            hallucination_flags=unsupported,
            errors=errors,
            correctness_ok=correctness_ok,
            completeness_ok=completeness.ok,
            requires_reextraction=bool(critical_unsupported),
        )
        return result, AuditEntry(
            agent=self.name,
            action="verify_submission",
            reason="Validate grounding, W-2 invariants, arithmetic, completeness",
            details={
                "valid": result.valid,
                "confidence": result.confidence_score,
                "correctness_ok": correctness_ok,
                "completeness_ok": completeness.ok,
                "requires_reextraction": result.requires_reextraction,
                "errors": result.errors,
            },
        )

    @staticmethod
    def _check(
        checks: list[VerificationCheck],
        name: str,
        condition: bool,
        passed: str,
        failed: str,
        weight: float,
    ) -> None:
        checks.append(
            VerificationCheck(
                name=name,
                passed=bool(condition),
                message=passed if condition else failed,
                weight=weight,
            )
        )


def _has_ssn(ssn: str) -> bool:
    import re

    return len(re.sub(r"\D", "", ssn or "")) == 9


def _total_income(data: TaxpayerData) -> Decimal:
    return (
        data.wages
        + data.taxable_interest
        + data.ordinary_dividends
        + data.long_term_capital_gain
        + data.short_term_capital_gain
        + data.self_employment_income
        + data.other_income
    )
