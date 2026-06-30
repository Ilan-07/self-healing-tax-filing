"""Idaho individual income tax, 2025 (flat-rate reference pack).

Idaho applies a single flat rate to Idaho taxable income, which conforms closely
to federal taxable income; this pack starts from federal taxable income as a
documented approximation. HB 40 (2025) cut the rate to 5.3%, retroactive to
January 1, 2025.

Sources:
  * Idaho Code 63-3024 (individual income tax rate).
  * HB 40 (2025) reducing the rate to 5.3% effective 2025-01-01.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 ID Form 40.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_TAXABLE_INCOME, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="ID",
        year=2025,
        source="Idaho Code 63-3024; HB 40 (2025) flat 5.3% for 2025",
        verified=False,
        rate=Decimal("0.053"),
        base=FEDERAL_TAXABLE_INCOME,
    )
)
