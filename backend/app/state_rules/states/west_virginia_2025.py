"""West Virginia individual income tax, 2025 (progressive-bracket reference pack).

West Virginia's five-band schedule reflects the 2023+ rate cuts (top 5.12%).
Single, MFJ, and HOH share one schedule; MFS uses half the edges. Applied to
federal AGI as a documented approximation; West Virginia uses personal
exemptions (no standard deduction), which are not modeled.

Sources:
  * W. Va. Code 11-21-4e (individual income tax rate schedule); HB 2526 (2023).
  * West Virginia Tax Division 2024 rate schedules.

``verified=False``: brackets transcribed from the cited schedules, not yet
reconciled against the published 2025 WV Form IT-140.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("10000"), D("0.0236")),
    (D("25000"), D("0.0315")),
    (D("40000"), D("0.0354")),
    (D("60000"), D("0.0472")),
    (None, D("0.0512")),
]

# Married Filing Separately uses half the single bracket edges.
_MFS = [
    (D("5000"), D("0.0236")),
    (D("12500"), D("0.0315")),
    (D("20000"), D("0.0354")),
    (D("30000"), D("0.0472")),
    (None, D("0.0512")),
]

PACK = register(
    BracketStatePack(
        state="WV",
        year=2025,
        source="W. Va. Code 11-21-4e; HB 2526 (2023); WV Tax Division schedules",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _MFS,
        },
    )
)
