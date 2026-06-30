"""Iowa individual income tax, 2025 (flat-rate reference pack).

Iowa's multi-year reform reaches a single 3.8% flat rate for tax year 2025
(replacing the prior graduated schedule). Applied to federal AGI as a documented
approximation; Iowa's own adjustments, deductions, and exemption credits are not
modeled.

Sources:
  * Iowa Code 422.5A (individual income tax rate).
  * S.F. 2442 (2024) accelerating the 3.8% flat rate to 2025.

``verified=False``: rate transcribed from the cited summary, not yet reconciled
against the published 2025 IA 1040.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="IA",
        year=2025,
        source="Iowa Code 422.5A; S.F. 2442 (2024) flat 3.8% for 2025",
        verified=False,
        rate=Decimal("0.038"),
        base=FEDERAL_AGI,
    )
)
