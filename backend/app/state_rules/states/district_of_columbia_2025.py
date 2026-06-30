"""District of Columbia individual income tax, 2025 (progressive-bracket pack).

DC's seven-band schedule tops out at 10.75% and is identical across filing
statuses. DC allows the federal standard deduction, so this pack uses
``base=federal_taxable_income``. DC's personal exemption and credits are not
modeled. (DC is a jurisdiction, not a state; the USPS code "DC" is used.)

Sources:
  * D.C. Code 47-1806.03 (individual income tax rates).
  * DC Office of Tax & Revenue rate schedule.

``verified=False``: brackets transcribed from the cited schedule, not yet
reconciled against the published 2025 DC Form D-40.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SCHEDULE = [
    (D("10000"), D("0.04")),
    (D("40000"), D("0.06")),
    (D("60000"), D("0.065")),
    (D("250000"), D("0.085")),
    (D("500000"), D("0.0925")),
    (D("1000000"), D("0.0975")),
    (None, D("0.1075")),
]

PACK = register(
    BracketStatePack(
        state="DC",
        year=2025,
        source="D.C. Code 47-1806.03; DC Office of Tax & Revenue schedule",
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
