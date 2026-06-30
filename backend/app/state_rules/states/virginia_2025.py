"""Virginia individual income tax, 2025 (progressive-bracket reference pack).

Virginia's four-band schedule (2% / 3% / 5% / 5.75%) tops out at 5.75% on income
over $17,000 and is identical across filing statuses. Virginia starts from
Virginia taxable income (federal AGI less the VA standard deduction and personal
exemptions); this pack applies the VA standard deduction to federal AGI as a
documented approximation and does not model personal/dependent exemptions or
age deductions.

Sources:
  * Va. Code 58.1-320 (individual income tax rates).
  * Va. Dept. of Taxation 2025 standard deduction ($8,500 / $17,000 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 VA Form 760.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

_SCHEDULE = [
    (Decimal("3000"), Decimal("0.02")),
    (Decimal("5000"), Decimal("0.03")),
    (Decimal("17000"), Decimal("0.05")),
    (None, Decimal("0.0575")),
]

PACK = register(
    BracketStatePack(
        state="VA",
        year=2025,
        source="Va. Code 58.1-320; VA Dept. of Taxation 2025 std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
        standard_deduction={
            FilingStatus.SINGLE: Decimal("8500"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("8500"),
            FilingStatus.MARRIED_JOINTLY: Decimal("17000"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("8500"),
        },
    )
)
