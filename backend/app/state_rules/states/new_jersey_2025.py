"""New Jersey gross income tax (progressive-bracket reference pack).

New Jersey uses two rate schedules: one for Single / MFS, one for MFJ / HOH /
QSS, topping out at 10.75% over $1,000,000. New Jersey has no standard
deduction (it allows personal exemptions instead, which are not modeled), and
its gross-income base differs from federal AGI; this pack starts from federal
AGI as a documented approximation.

Sources:
  * N.J.S.A. 54A:2-1 (gross income tax rate schedules).
  * N.J. Division of Taxation 2024 tax-rate schedules (NJ-1040).

``verified=False``: brackets transcribed from the cited schedules, not yet
reconciled against the published 2025 NJ-1040. Personal exemptions and NJ-specific
income adjustments are not modeled.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

# Single and Married Filing Separately.
_SINGLE = [
    (D("20000"), D("0.014")),
    (D("35000"), D("0.0175")),
    (D("40000"), D("0.035")),
    (D("75000"), D("0.05525")),
    (D("500000"), D("0.0637")),
    (D("1000000"), D("0.0897")),
    (None, D("0.1075")),
]

# Married Filing Jointly, Head of Household, Qualifying Surviving Spouse.
_JOINT = [
    (D("20000"), D("0.014")),
    (D("50000"), D("0.0175")),
    (D("70000"), D("0.0245")),
    (D("80000"), D("0.035")),
    (D("150000"), D("0.05525")),
    (D("500000"), D("0.0637")),
    (D("1000000"), D("0.0897")),
    (None, D("0.1075")),
]

PACK = register(
    BracketStatePack(
        state="NJ",
        year=2025,
        source="N.J.S.A. 54A:2-1; NJ Division of Taxation NJ-1040 rate schedules",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _JOINT,
            FilingStatus.HEAD_OF_HOUSEHOLD: _JOINT,
        },
    )
)
