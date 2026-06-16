"""Structural self-consistency checks for tax-year parameters.

These catch transcription errors (non-monotonic brackets, MFS standard deduction
that doesn't equal single, mis-ordered phase-outs) independently of whether a
year is marked ``verified``. Run over the whole registry in the test suite.
"""

from __future__ import annotations

from app.schemas import FilingStatus
from app.tax_rules.params import TaxYearParams


def validate_params(p: TaxYearParams) -> list[str]:
    issues: list[str] = []

    def note(cond: bool, msg: str) -> None:
        if not cond:
            issues.append(f"[{p.year}] {msg}")

    # Standard deduction
    for fs, amount in p.standard_deductions.items():
        note(amount > 0, f"standard deduction for {fs} must be positive")
    note(
        p.standard_deductions[FilingStatus.MARRIED_SEPARATELY]
        == p.standard_deductions[FilingStatus.SINGLE],
        "MFS standard deduction must equal single",
    )
    note(p.additional_std_married > 0 and p.additional_std_unmarried > 0,
         "additional standard deductions must be positive")

    # Brackets: upper bounds strictly increasing, rates non-decreasing, open top.
    for fs, brackets in p.brackets.items():
        last_upper = None
        prev_rate = None
        for i, (upper, rate) in enumerate(brackets):
            if i == len(brackets) - 1:
                note(upper is None, f"{fs} brackets must end with an open band")
            else:
                note(upper is not None, f"{fs} non-final band missing upper bound")
                if upper is not None and last_upper is not None:
                    note(upper > last_upper, f"{fs} bracket bounds not increasing")
                last_upper = upper
            if prev_rate is not None:
                note(rate >= prev_rate, f"{fs} bracket rates not non-decreasing")
            prev_rate = rate

    # Preferential breakpoints ordered
    for fs in p.preferential.zero_rate_max:
        note(
            p.preferential.zero_rate_max[fs] < p.preferential.fifteen_rate_max[fs],
            f"{fs} 0% breakpoint must be below 15% breakpoint",
        )

    # Rates within (0, 1)
    for name, rate in (
        ("ss_rate", p.ss_rate),
        ("medicare_rate", p.medicare_rate),
        ("addl_medicare_rate", p.addl_medicare_rate),
        ("niit_rate", p.niit_rate),
        ("qbi_rate", p.qbi_rate),
    ):
        note(0 < rate < 1, f"{name} must be between 0 and 1")
    note(p.ss_wage_base > 0, "ss_wage_base must be positive")
    note(p.credits.ctc_per_child > 0, "CTC per child must be positive")

    if p.eitc is not None:
        note(p.eitc.investment_income_limit > 0, "EITC investment limit must be > 0")
        for n, tier in p.eitc.tiers.items():
            note(tier.max_credit > 0, f"EITC tier {n} max credit must be > 0")
            note(
                tier.phaseout_begin_mfj >= tier.phaseout_begin_other,
                f"EITC tier {n} MFJ phase-out must be >= other",
            )

    if p.amt is not None:
        for fs, exemption in p.amt.exemption.items():
            note(exemption > 0, f"AMT exemption for {fs} must be positive")
            note(
                p.amt.phaseout_start[fs] > exemption,
                f"AMT phase-out for {fs} must exceed the exemption",
            )

    return issues


def validate_all(registry: dict[int, TaxYearParams]) -> list[str]:
    issues: list[str] = []
    for params in registry.values():
        issues.extend(validate_params(params))
    return issues
