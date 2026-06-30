"""Kentucky individual income tax, 2025 (flat-rate reference pack).

Flat 4.0% of federal AGI less Kentucky's standard deduction. Kentucky's
standard deduction does not vary by filing status.

Sources:
  * KRS 141.020 (4.0% flat individual rate for 2025).
  * Kentucky DOR 2025 standard deduction ($3,270).

``verified=False``: rate and standard deduction transcribed from the cited
summary, not yet reconciled against the published 2025 KY Form 740.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

_STD = Decimal("3270")

PACK = register(
    FlatStatePack(
        state="KY",
        year=2025,
        source="KRS 141.020; KY DOR 2025 rate 4.0%, std deduction $3,270",
        verified=False,
        rate=Decimal("0.040"),
        base=FEDERAL_AGI,
        standard_deduction={
            FilingStatus.SINGLE: _STD,
            FilingStatus.MARRIED_SEPARATELY: _STD,
            FilingStatus.MARRIED_JOINTLY: _STD,
            FilingStatus.HEAD_OF_HOUSEHOLD: _STD,
        },
    )
)
