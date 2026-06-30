"""Minnesota individual income tax (progressive-bracket reference pack).

Minnesota's four-band schedule (5.35% / 6.8% / 7.85% / 9.85%) uses separate
bracket edges for Single, MFS, MFJ, and HOH. Minnesota taxable income begins at
federal taxable income (federal standard/itemized deduction already applied),
so this pack uses ``base=federal_taxable_income`` with no additional state
deduction. Minnesota's own additions/subtractions and credits are not modeled.

Sources:
  * Minn. Stat. 290.06 subd. 2c (individual income tax rate schedule).
  * Minnesota DOR indexed bracket tables (2024 tax year).

``verified=False``: brackets transcribed from the 2024-indexed DOR tables, not
yet reconciled against the published 2025 MN Form M1; a maintainer must update
to the 2025-indexed edges before flipping ``verified``.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("31690"), D("0.0535")),
    (D("104090"), D("0.068")),
    (D("193240"), D("0.0785")),
    (None, D("0.0985")),
]

_MFS = [
    (D("23165"), D("0.0535")),
    (D("92020"), D("0.068")),
    (D("160725"), D("0.0785")),
    (None, D("0.0985")),
]

_MFJ = [
    (D("46330"), D("0.0535")),
    (D("184040"), D("0.068")),
    (D("321450"), D("0.0785")),
    (None, D("0.0985")),
]

_HOH = [
    (D("39010"), D("0.0535")),
    (D("156760"), D("0.068")),
    (D("256880"), D("0.0785")),
    (None, D("0.0985")),
]

PACK = register(
    BracketStatePack(
        state="MN",
        year=2025,
        source="Minn. Stat. 290.06 subd. 2c; MN DOR 2024-indexed brackets",
        verified=False,
        base=FEDERAL_TAXABLE_INCOME,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _MFS,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
    )
)
