"""Georgia individual income tax, 2025 (flat-rate reference pack).

Georgia moved to a flat individual rate under HB 1437 (2022) with scheduled
annual reductions; HB 111 (2025) accelerated the tax-year-2025 rate to 5.19%.
Applied to federal AGI less Georgia's standard deduction; Georgia's personal
exemption / dependent allowances are not modeled.

Sources:
  * O.C.G.A. 48-7-20 (individual income tax rate).
  * HB 111 (2025) accelerating the 2025 flat rate to 5.19%.
  * Georgia DOR 2024+ standard deduction ($12,000 / $24,000 MFJ).

``verified=False``: rate and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 GA Form 500.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="GA",
        year=2025,
        source="O.C.G.A. 48-7-20; HB 111 (2025) flat 5.19% for 2025",
        verified=False,
        rate=Decimal("0.0519"),
        base=FEDERAL_AGI,
        standard_deduction={
            FilingStatus.SINGLE: Decimal("12000"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("12000"),
            FilingStatus.MARRIED_JOINTLY: Decimal("24000"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("12000"),
        },
    )
)
