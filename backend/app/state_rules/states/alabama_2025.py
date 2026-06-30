"""Alabama individual income tax, 2025 (progressive-bracket reference pack).

Alabama's three-band schedule (2% / 4% / 5%) uses doubled bracket edges for MFJ.
Applied to federal AGI as a documented approximation; Alabama's income-phased
standard deduction and personal/dependent exemptions are not modeled.

Sources:
  * Ala. Code 40-18-5 (individual income tax rates).
  * Alabama DOR 2024 rate schedules.

``verified=False``: brackets transcribed from the cited schedules, not yet
reconciled against the published 2025 AL Form 40.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("500"), D("0.02")),
    (D("3000"), D("0.04")),
    (None, D("0.05")),
]

_MFJ = [
    (D("1000"), D("0.02")),
    (D("6000"), D("0.04")),
    (None, D("0.05")),
]

PACK = register(
    BracketStatePack(
        state="AL",
        year=2025,
        source="Ala. Code 40-18-5; Alabama DOR 2024 rate schedules",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
    )
)
