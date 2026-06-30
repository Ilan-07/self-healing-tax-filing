"""Ohio individual income tax, 2025 (progressive-bracket reference pack).

Ohio's multi-year reform leaves a near-flat schedule for 2025: the first
$26,050 of income is untaxed, income to $100,000 is taxed at 2.75%, and income
above $100,000 at 3.5%. Modeled as a three-band schedule (0% / 2.75% / 3.5%),
identical across filing statuses. Ohio starts from Ohio taxable income (federal
AGI less Ohio adjustments and personal/dependent exemptions); this pack uses
federal AGI as a documented approximation and does not model exemptions, the
joint-filer credit, or the business-income deduction.

Sources:
  * Ohio Rev. Code 5747.02 (individual income tax rates).
  * Ohio Dept. of Taxation 2025 income tax brackets.

``verified=False``: brackets transcribed from the cited summary, not yet
reconciled against the published 2025 Ohio IT 1040.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

_SCHEDULE = [
    (Decimal("26050"), Decimal("0")),
    (Decimal("100000"), Decimal("0.0275")),
    (None, Decimal("0.035")),
]

PACK = register(
    BracketStatePack(
        state="OH",
        year=2025,
        source="Ohio Rev. Code 5747.02; OH Dept. of Taxation 2025 brackets",
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
