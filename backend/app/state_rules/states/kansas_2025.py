"""Kansas individual income tax, 2025 (progressive-bracket reference pack).

Kansas's 2024 reform left a two-band schedule (5.2% / 5.58%) with doubled
bracket edges for MFJ. Applied to federal AGI less the Kansas standard deduction
as a documented approximation; Kansas exemptions/credits are not modeled.

Sources:
  * Kan. Stat. 79-32,110 (individual income tax rates).
  * S.B. 1 (2024 Special Session) two-band schedule.
  * Kansas DOR standard deduction ($3,605 / $8,240 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 KS Form K-40.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("23000"), D("0.052")),
    (None, D("0.0558")),
]

_MFJ = [
    (D("46000"), D("0.052")),
    (None, D("0.0558")),
]

PACK = register(
    BracketStatePack(
        state="KS",
        year=2025,
        source="Kan. Stat. 79-32,110; S.B. 1 (2024) two-band; KS DOR std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("3605"),
            FilingStatus.MARRIED_SEPARATELY: D("3605"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("6180"),
            FilingStatus.MARRIED_JOINTLY: D("8240"),
        },
    )
)
