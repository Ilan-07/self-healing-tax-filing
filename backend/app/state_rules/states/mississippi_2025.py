"""Mississippi individual income tax, 2025 (reference pack).

Mississippi exempts the first $10,000 of taxable income and taxes the remainder
at a flat 4.4% for 2025. That is naturally a two-band progressive schedule
(0% then 4.4%), identical across filing statuses. Modeled on federal AGI as a
documented approximation; MS exemptions/deductions are not modeled.

Sources:
  * Miss. Code 27-7-5 (2025 rate 4.4% above the $10,000 exemption).
  * Mississippi DOR 2025 individual income tax guidance.

``verified=False``: rate and exempt floor transcribed from the cited summary,
not yet reconciled against the published 2025 MS Form 80-105.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

_SCHEDULE = [
    (Decimal("10000"), Decimal("0")),
    (None, Decimal("0.044")),
]

PACK = register(
    BracketStatePack(
        state="MS",
        year=2025,
        source="Miss. Code 27-7-5; MS DOR 2025 rate 4.4% over $10,000",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
    )
)
