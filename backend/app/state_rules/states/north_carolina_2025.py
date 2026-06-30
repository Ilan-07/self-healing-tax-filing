"""North Carolina individual income tax, 2025 (flat-rate reference pack).

Flat 4.25% of federal AGI less North Carolina's standard deduction (which does
vary by filing status). State-specific additions/deductions are not modeled.

Sources:
  * N.C.G.S. 105-153.7 (2025 rate 4.25%).
  * N.C. Dept. of Revenue 2025 standard deduction amounts.

``verified=False``: rate and standard deduction transcribed from the cited
summary, not yet reconciled against the published 2025 NC D-400.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="NC",
        year=2025,
        source="N.C.G.S. 105-153.7; NC DOR 2025 rate 4.25%",
        verified=False,
        rate=Decimal("0.0425"),
        base=FEDERAL_AGI,
        standard_deduction={
            FilingStatus.SINGLE: Decimal("12750"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("12750"),
            FilingStatus.MARRIED_JOINTLY: Decimal("25500"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("19125"),
        },
    )
)
