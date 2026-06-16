"""Completeness checks: 'did we capture all the income?' -- distinct from
correctness ('is the math right?').

The gold-standard check reconciles the extracted documents against the IRS
Wage & Income transcript (what third parties already reported). In this build a
transcript is optional; when present (e.g. emitted by the synthetic generator)
each transcript line with no matching extracted value is flagged as missing
income. Without a transcript we fall back to lightweight coverage heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas import TaxpayerData


# Transcript field -> the TaxpayerData attribute it should map to.
TRANSCRIPT_FIELDS = {
    "wages": "wages",
    "taxable_interest": "taxable_interest",
    "ordinary_dividends": "ordinary_dividends",
    "self_employment_income": "self_employment_income",
    "long_term_capital_gain": "long_term_capital_gain",
}

TOLERANCE = Decimal("1")


@dataclass
class CompletenessReport:
    ok: bool
    issues: list[str] = field(default_factory=list)


def check_completeness(
    data: TaxpayerData, transcript: dict[str, object] | None = None
) -> CompletenessReport:
    issues: list[str] = []

    if transcript:
        for t_field, attr in TRANSCRIPT_FIELDS.items():
            if t_field not in transcript:
                continue
            reported = _decimal(transcript[t_field])
            captured = Decimal(getattr(data, attr))
            if reported > 0 and abs(reported - captured) > TOLERANCE:
                issues.append(
                    f"Transcript reports {t_field}={reported} but extracted "
                    f"{captured}; income may be missing or misread."
                )
    else:
        # No transcript: heuristic coverage signals only.
        has_income = any(
            getattr(data, attr) > 0
            for attr in (
                "wages",
                "taxable_interest",
                "ordinary_dividends",
                "self_employment_income",
                "long_term_capital_gain",
                "short_term_capital_gain",
                "other_income",
            )
        )
        if not has_income:
            issues.append("No income of any kind was captured.")
        if data.qualified_dividends > data.ordinary_dividends:
            issues.append(
                "Qualified dividends exceed ordinary dividends "
                "(qualified are a subset of ordinary)."
            )

    return CompletenessReport(ok=not issues, issues=issues)


def _decimal(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))
