"""Nebraska individual income tax, 2025 (progressive-bracket reference pack).

Nebraska's four-band schedule tops out at 5.20% for 2025 (reduced from prior
years) and uses doubled bracket edges for MFJ. Applied to federal AGI less the
Nebraska standard deduction as a documented approximation; Nebraska's personal
exemption credit is not modeled.

Sources:
  * Neb. Rev. Stat. 77-2715.03 (individual income tax rates); LB 754 (2023)
    rate reductions.
  * Nebraska DOR standard deduction ($8,300 / $16,600 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 NE Form 1040N.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("3700"), D("0.0246")),
    (D("22170"), D("0.0351")),
    (D("35730"), D("0.0501")),
    (None, D("0.052")),
]

_MFJ = [
    (D("7390"), D("0.0246")),
    (D("44350"), D("0.0351")),
    (D("71460"), D("0.0501")),
    (None, D("0.052")),
]

PACK = register(
    BracketStatePack(
        state="NE",
        year=2025,
        source="Neb. Rev. Stat. 77-2715.03; LB 754 (2023); NE DOR std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("8300"),
            FilingStatus.MARRIED_SEPARATELY: D("8300"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("12150"),
            FilingStatus.MARRIED_JOINTLY: D("16600"),
        },
    )
)
