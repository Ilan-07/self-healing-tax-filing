"""Louisiana individual income tax, 2025 (flat-rate reference pack).

Louisiana's 2024 special-session reform replaced the graduated schedule with a
single 3.0% flat rate effective tax year 2025. Applied to federal AGI as a
documented approximation; Louisiana's combined personal exemption / standard
deduction and excess-federal-itemized deduction are not modeled.

Sources:
  * La. R.S. 47:32 (individual income tax rate).
  * Act 11 (2024 Third Extraordinary Session) flat 3.0% for 2025.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 LA IT-540.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="LA",
        year=2025,
        source="La. R.S. 47:32; Act 11 (2024 3rd Ex. Sess.) flat 3.0% for 2025",
        verified=False,
        rate=Decimal("0.030"),
        base=FEDERAL_AGI,
    )
)
