"""Delaware individual income tax, 2025 (progressive-bracket reference pack).

Delaware's six-band schedule (0% to 6.6%) is identical across filing statuses.
Applied to federal AGI less the Delaware standard deduction as a documented
approximation; Delaware's personal credits are not modeled.

Sources:
  * 30 Del. C. 1102 (individual income tax rates).
  * Delaware Division of Revenue standard deduction ($3,250 / $6,500 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 DE Form 200.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SCHEDULE = [
    (D("2000"), D("0")),
    (D("5000"), D("0.022")),
    (D("10000"), D("0.039")),
    (D("20000"), D("0.048")),
    (D("25000"), D("0.052")),
    (D("60000"), D("0.0555")),
    (None, D("0.066")),
]

PACK = register(
    BracketStatePack(
        state="DE",
        year=2025,
        source="30 Del. C. 1102; DE Division of Revenue std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("3250"),
            FilingStatus.MARRIED_SEPARATELY: D("3250"),
            FilingStatus.MARRIED_JOINTLY: D("6500"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("3250"),
        },
    )
)
