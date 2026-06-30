"""Wisconsin individual income tax (progressive-bracket reference pack).

Wisconsin's four-band schedule (3.50% / 4.40% / 5.30% / 7.65%) uses separate
bracket edges for Single/HOH than for MFJ; MFS uses half the MFJ edges. Applied
to federal AGI as a documented approximation.

Wisconsin's standard deduction is a sliding-scale amount that phases out as
income rises (eliminated entirely around $130k single); the fixed-amount pack
cannot represent that, so it is **not modeled** -- this overstates tax at
low-to-mid incomes. Wisconsin subtractions and credits are also not modeled.

Sources:
  * Wis. Stat. 71.06 (individual income tax rate schedule).
  * Wisconsin DOR indexed bracket tables (2024 tax year).

``verified=False``: brackets transcribed from the 2024-indexed DOR tables, not
yet reconciled against the published 2025 WI Form 1.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

# Single and Head of Household.
_SINGLE = [
    (D("14680"), D("0.035")),
    (D("29370"), D("0.044")),
    (D("323290"), D("0.053")),
    (None, D("0.0765")),
]

# Married Filing Jointly.
_MFJ = [
    (D("19580"), D("0.035")),
    (D("39150"), D("0.044")),
    (D("431060"), D("0.053")),
    (None, D("0.0765")),
]

# Married Filing Separately (half the MFJ edges).
_MFS = [
    (D("9790"), D("0.035")),
    (D("19575"), D("0.044")),
    (D("215530"), D("0.053")),
    (None, D("0.0765")),
]

PACK = register(
    BracketStatePack(
        state="WI",
        year=2025,
        source="Wis. Stat. 71.06; WI DOR 2024-indexed brackets",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.MARRIED_SEPARATELY: _MFS,
        },
    )
)
