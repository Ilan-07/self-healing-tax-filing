"""Colorado individual income tax, 2025 (flat-rate reference pack).

Colorado's return begins at *federal taxable income* (Form DR 0104 line 1) and
applies a single flat rate with no state standard deduction. The 2025 rate is
4.40%.

Sources:
  * C.R.S. 39-22-104 (flat-rate individual income tax).
  * Colorado Department of Revenue, 2025 individual income tax rate (4.40%).

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published DR 0104 in this environment.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_TAXABLE_INCOME, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="CO",
        year=2025,
        source="C.R.S. 39-22-104; CO DOR 2025 rate 4.40%",
        verified=False,
        rate=Decimal("0.0440"),
        base=FEDERAL_TAXABLE_INCOME,
    )
)
