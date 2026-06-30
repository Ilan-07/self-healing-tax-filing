"""South Carolina individual income tax, 2025 (progressive-bracket reference pack).

South Carolina applies a three-band schedule (0% / 3% / top rate) to South
Carolina taxable income, which begins at federal taxable income; this pack uses
``base=federal_taxable_income``. The schedule is identical across filing
statuses.

The 2025 top rate is subject to a revenue trigger: 6.2% if the trigger is met,
otherwise 6.3%. This pack assumes **6.2%** -- a maintainer should confirm against
the SC DOR 2025 schedule and adjust before flipping ``verified``. SC's own
deductions/credits are not modeled.

Sources:
  * S.C. Code 12-6-510 (individual income tax rate schedule).
  * S.C. DOR 2024-indexed brackets; 2025 top rate 6.2% (trigger-dependent).

``verified=False``: brackets transcribed from the 2024-indexed tables with the
assumed 2025 top rate, not yet reconciled against the published 2025 SC1040.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

_SCHEDULE = [
    (Decimal("3460"), Decimal("0")),
    (Decimal("17330"), Decimal("0.03")),
    (None, Decimal("0.062")),
]

PACK = register(
    BracketStatePack(
        state="SC",
        year=2025,
        source="S.C. Code 12-6-510; SC DOR 2024-indexed brackets, 6.2% top (trigger)",
        verified=False,
        base=FEDERAL_TAXABLE_INCOME,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
    )
)
