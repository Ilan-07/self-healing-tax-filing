"""Oklahoma individual income tax, 2025 (progressive-bracket reference pack).

Oklahoma's six-band schedule tops out at 4.75% with doubled bracket edges for
MFJ. Applied to federal AGI less the Oklahoma standard deduction as a documented
approximation; Oklahoma's personal exemptions are not modeled.

Sources:
  * Okla. Stat. tit. 68 2355 (individual income tax rates).
  * Oklahoma Tax Commission standard deduction ($6,350 / $12,700 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 OK Form 511.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("1000"), D("0.0025")),
    (D("2500"), D("0.0075")),
    (D("3750"), D("0.0175")),
    (D("4900"), D("0.0275")),
    (D("7200"), D("0.0375")),
    (None, D("0.0475")),
]

_MFJ = [
    (D("2000"), D("0.0025")),
    (D("5000"), D("0.0075")),
    (D("7500"), D("0.0175")),
    (D("9800"), D("0.0275")),
    (D("12200"), D("0.0375")),
    (None, D("0.0475")),
]

PACK = register(
    BracketStatePack(
        state="OK",
        year=2025,
        source="Okla. Stat. tit. 68 2355; OK Tax Commission std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("6350"),
            FilingStatus.MARRIED_SEPARATELY: D("6350"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("9350"),
            FilingStatus.MARRIED_JOINTLY: D("12700"),
        },
    )
)
