"""Illinois individual income tax, 2025 (flat-rate reference pack).

Flat rate applied to federal AGI. State-specific exemptions/credits are not
modeled; the result is a documented approximation, not a filed-return figure.

Sources:
  * 35 ILCS 5/201
  * Illinois DOR 2025 individual income tax guidance.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 Illinois return.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="IL",
        year=2025,
        source="35 ILCS 5/201; 2025 flat rate 0.0495",
        verified=False,
        rate=Decimal("0.0495"),
        base=FEDERAL_AGI,
    )
)
