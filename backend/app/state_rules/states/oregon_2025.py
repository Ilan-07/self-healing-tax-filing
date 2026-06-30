"""Oregon individual income tax (progressive-bracket reference pack).

Oregon's four-band schedule (4.75% / 6.75% / 8.75% / 9.9%) uses separate bracket
edges for Single/MFS than for MFJ/HOH. Applied to federal AGI less the Oregon
standard deduction as a documented approximation.

Oregon allows an income-limited subtraction for federal income tax liability
(up to a capped amount) that materially lowers Oregon tax; because it depends on
federal liability it is **not modeled** here, so this pack overstates Oregon tax.
Oregon additions/subtractions and the exemption credit are also not modeled.

Sources:
  * O.R.S. 316.037 (individual income tax rate schedule).
  * Oregon DOR 2024-indexed brackets and standard deduction.

``verified=False``: brackets and standard deduction transcribed from the
2024-indexed tables, not yet reconciled against the published 2025 OR Form OR-40.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

# Single and Married Filing Separately.
_SINGLE = [
    (D("4300"), D("0.0475")),
    (D("10750"), D("0.0675")),
    (D("125000"), D("0.0875")),
    (None, D("0.099")),
]

# Married Filing Jointly and Head of Household.
_JOINT = [
    (D("8600"), D("0.0475")),
    (D("21500"), D("0.0675")),
    (D("250000"), D("0.0875")),
    (None, D("0.099")),
]

PACK = register(
    BracketStatePack(
        state="OR",
        year=2025,
        source="O.R.S. 316.037; Oregon DOR 2024-indexed brackets + std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _JOINT,
            FilingStatus.HEAD_OF_HOUSEHOLD: _JOINT,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("2745"),
            FilingStatus.MARRIED_SEPARATELY: D("2745"),
            FilingStatus.MARRIED_JOINTLY: D("5495"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("4420"),
        },
    )
)
