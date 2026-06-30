"""Hawaii individual income tax, 2025 (progressive-bracket reference pack).

Hawaii's twelve-band schedule tops out at 11%. MFJ uses doubled bracket edges;
HOH is approximated with the single schedule. Applied to federal AGI less the
Hawaii standard deduction as a documented approximation; Hawaii's exemptions are
not modeled.

Sources:
  * Haw. Rev. Stat. 235-51 (individual income tax rates).
  * Hawaii DOTAX standard deduction ($2,200 / $4,400 MFJ).

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 HI Form N-11. HOH is
approximated with the single schedule.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("2400"), D("0.014")),
    (D("4800"), D("0.032")),
    (D("9600"), D("0.055")),
    (D("14400"), D("0.064")),
    (D("19200"), D("0.068")),
    (D("24000"), D("0.072")),
    (D("36000"), D("0.076")),
    (D("48000"), D("0.079")),
    (D("150000"), D("0.0825")),
    (D("175000"), D("0.09")),
    (D("200000"), D("0.10")),
    (None, D("0.11")),
]

_MFJ = [
    (D("4800"), D("0.014")),
    (D("9600"), D("0.032")),
    (D("19200"), D("0.055")),
    (D("28800"), D("0.064")),
    (D("38400"), D("0.068")),
    (D("48000"), D("0.072")),
    (D("72000"), D("0.076")),
    (D("96000"), D("0.079")),
    (D("300000"), D("0.0825")),
    (D("350000"), D("0.09")),
    (D("400000"), D("0.10")),
    (None, D("0.11")),
]

PACK = register(
    BracketStatePack(
        state="HI",
        year=2025,
        source="Haw. Rev. Stat. 235-51; Hawaii DOTAX std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("2200"),
            FilingStatus.MARRIED_SEPARATELY: D("2200"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("3212"),
            FilingStatus.MARRIED_JOINTLY: D("4400"),
        },
    )
)
