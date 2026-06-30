"""Rhode Island individual income tax, 2025 (progressive-bracket reference pack).

Rhode Island's three-band schedule (3.75% / 4.75% / 5.99%) is identical across
filing statuses. Applied to federal AGI less the Rhode Island standard deduction
as a documented approximation; RI's standard deduction phase-out and exemptions
are not modeled.

Sources:
  * R.I. Gen. Laws 44-30-2.6 (individual income tax rates).
  * Rhode Island Division of Taxation standard deduction ($10,550 / $21,150 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 RI-1040.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SCHEDULE = [
    (D("77450"), D("0.0375")),
    (D("176050"), D("0.0475")),
    (None, D("0.0599")),
]

PACK = register(
    BracketStatePack(
        state="RI",
        year=2025,
        source="R.I. Gen. Laws 44-30-2.6; RI Division of Taxation std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("10550"),
            FilingStatus.MARRIED_SEPARATELY: D("10550"),
            FilingStatus.MARRIED_JOINTLY: D("21150"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("15825"),
        },
    )
)
