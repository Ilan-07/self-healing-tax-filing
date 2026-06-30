"""Utah individual income tax, 2025 (flat-rate reference pack).

Flat rate applied to federal AGI. State-specific exemptions/credits are not
modeled; the result is a documented approximation, not a filed-return figure.

Sources:
  * Utah Code 59-10-104
  * Utah DOR 2025 individual income tax guidance.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 Utah return.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="UT",
        year=2025,
        source="Utah Code 59-10-104; 2025 flat rate 0.0455",
        verified=False,
        rate=Decimal("0.0455"),
        base=FEDERAL_AGI,
    )
)
