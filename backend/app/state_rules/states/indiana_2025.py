"""Indiana individual income tax, 2025 (flat-rate reference pack).

Flat rate applied to federal AGI. State-specific exemptions/credits are not
modeled; the result is a documented approximation, not a filed-return figure.

Sources:
  * Ind. Code 6-3-2-1
  * Indiana DOR 2025 individual income tax guidance.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 Indiana return.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="IN",
        year=2025,
        source="Ind. Code 6-3-2-1; 2025 flat rate 0.0300",
        verified=False,
        rate=Decimal("0.0300"),
        base=FEDERAL_AGI,
    )
)
