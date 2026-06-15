from decimal import Decimal

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import (
    AuditEntry,
    TaxCalculation,
    TaxpayerData,
    VerificationCheck,
    VerificationResult,
)


class VerificationAgent:
    name = "Verification Agent"

    def __init__(self, calculator: TaxCalculator, threshold: float):
        self.calculator = calculator
        self.threshold = threshold

    def run(
        self, data: TaxpayerData, calculation: TaxCalculation
    ) -> tuple[VerificationResult, AuditEntry]:
        checks: list[VerificationCheck] = []
        self._check(
            checks,
            "taxpayer_name",
            bool(data.employee_name.strip()),
            "Taxpayer name is present",
            "Taxpayer name is missing",
            1.5,
        )
        self._check(
            checks,
            "employer",
            bool(data.employer_name.strip()),
            "Employer is present",
            "Employer is missing",
            0.5,
        )
        self._check(
            checks,
            "income",
            data.wages > 0,
            "Positive wage income found",
            "Wage income is absent or non-positive",
            2,
        )
        self._check(
            checks,
            "withholding_bounds",
            data.federal_tax_withheld <= data.wages
            and data.state_tax_withheld <= data.wages,
            "Withholding values are within wage bounds",
            "A withholding value exceeds wages",
            2,
        )
        recalculated = self.calculator.calculate(data)
        arithmetic_ok = recalculated == calculation
        self._check(
            checks,
            "calculation_replay",
            arithmetic_ok,
            "Independent deterministic recalculation matched",
            "Calculation did not match deterministic replay",
            3,
        )
        supported_fields = {item.field for item in data.evidence}
        critical = {"wages", "federal_tax_withheld"}
        unsupported = [
            field
            for field in critical
            if getattr(data, field) != Decimal("0") and field not in supported_fields
        ]
        self._check(
            checks,
            "source_grounding",
            not unsupported,
            "Critical monetary values have source evidence",
            f"Unsupported critical fields: {', '.join(unsupported)}",
            3,
        )
        evidence_scores = [
            value
            for key, value in data.field_confidence.items()
            if key in supported_fields
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
        errors = [c.message for c in checks if not c.passed]
        result = VerificationResult(
            valid=not errors and confidence >= self.threshold,
            confidence_score=confidence,
            checks=checks,
            hallucination_flags=unsupported,
            errors=errors
            + (
                [f"Confidence {confidence:.1%} is below {self.threshold:.1%}"]
                if confidence < self.threshold
                else []
            ),
        )
        return result, AuditEntry(
            agent=self.name,
            action="verify_submission",
            reason="Validate source grounding, rules, and arithmetic",
            details={
                "valid": result.valid,
                "confidence": result.confidence_score,
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
                passed=condition,
                message=passed if condition else failed,
                weight=weight,
            )
        )
