"""Missouri individual income tax, 2025 (progressive-bracket reference pack).

Missouri exempts the first bracket of income and then steps up in 0.5% bands to
a top rate of 4.7% for 2025 (reduced from 4.8%). The schedule is identical
across filing statuses. Missouri's standard deduction equals the federal amount,
so Missouri taxable income tracks federal taxable income; this pack uses
``base=federal_taxable_income``. Missouri modifications (e.g. the partial
business-income deduction) and credits are not modeled.

Sources:
  * Mo. Rev. Stat. 143.011 (individual income tax rate schedule).
  * Missouri DOR 2024-indexed brackets; 2025 top rate 4.7%.

``verified=False``: brackets transcribed from the 2024-indexed tables with the
2025 top rate, not yet reconciled against the published 2025 MO-1040.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SCHEDULE = [
    (D("1273"), D("0")),
    (D("2546"), D("0.02")),
    (D("3819"), D("0.025")),
    (D("5092"), D("0.03")),
    (D("6365"), D("0.035")),
    (D("7638"), D("0.04")),
    (D("8911"), D("0.045")),
    (None, D("0.047")),
]

PACK = register(
    BracketStatePack(
        state="MO",
        year=2025,
        source="Mo. Rev. Stat. 143.011; MO DOR 2024-indexed brackets, 4.7% top",
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
