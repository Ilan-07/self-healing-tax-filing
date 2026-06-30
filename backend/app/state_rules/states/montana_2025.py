"""Montana individual income tax, 2025 (progressive-bracket reference pack).

Montana's 2024 reform left a two-band schedule (4.7% / 5.9%) tied to federal
taxable income; this pack uses ``base=federal_taxable_income`` with doubled
bracket edges for MFJ. Montana's own adjustments and credits are not modeled.

Sources:
  * Mont. Code 15-30-2103 (individual income tax rates).
  * Montana DOR 2024 two-band schedule.

``verified=False``: brackets transcribed from the cited schedule, not yet
reconciled against the published 2025 MT Form 2.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("20500"), D("0.047")),
    (None, D("0.059")),
]

_MFJ = [
    (D("41000"), D("0.047")),
    (None, D("0.059")),
]

PACK = register(
    BracketStatePack(
        state="MT",
        year=2025,
        source="Mont. Code 15-30-2103; Montana DOR 2024 two-band schedule",
        verified=False,
        base=FEDERAL_TAXABLE_INCOME,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
    )
)
