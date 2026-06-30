"""Michigan individual income tax, 2025 (flat-rate reference pack).

Flat rate applied to federal AGI. State-specific exemptions/credits are not
modeled; the result is a documented approximation, not a filed-return figure.

Sources:
  * MCL 206.51
  * Michigan DOR 2025 individual income tax guidance.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 Michigan return.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="MI",
        year=2025,
        source="MCL 206.51; 2025 flat rate 0.0425",
        verified=False,
        rate=Decimal("0.0425"),
        base=FEDERAL_AGI,
    )
)
