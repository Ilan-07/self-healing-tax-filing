"""Arizona individual income tax, 2025 (flat-rate reference pack).

Arizona moved to a single 2.5% flat rate effective 2023 (A.R.S. 43-1011) and
conforms its standard deduction to the federal amounts, so this pack starts from
federal taxable income as a documented approximation.

Sources:
  * A.R.S. 43-1011 (2.5% flat individual rate, 2023+).
  * Arizona DOR 2025 individual income tax guidance.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 AZ Form 140.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_TAXABLE_INCOME, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="AZ",
        year=2025,
        source="A.R.S. 43-1011; AZ DOR 2025 flat rate 2.5%",
        verified=False,
        rate=Decimal("0.025"),
        base=FEDERAL_TAXABLE_INCOME,
    )
)
