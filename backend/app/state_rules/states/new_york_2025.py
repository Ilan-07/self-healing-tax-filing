"""New York State individual income tax (progressive-bracket reference pack).

New York starts from federal AGI, subtracts a state standard deduction, and
applies a nine-band schedule (4%-10.9%). The tax-benefit recapture that
flattens the schedule at high incomes, NYC/Yonkers local taxes, and the
supplemental tax are **not** modeled here.

Sources:
  * N.Y. Tax Law sec. 601 (rate schedules).
  * N.Y. Dept. of Taxation & Finance standard deduction and rate tables.

``verified=False``: brackets and standard deduction transcribed from the cited
tables, not yet reconciled against the published 2025 NY IT-201. A maintainer
must reconcile (and decide whether to model recapture) before flipping
``verified``.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("8500"), D("0.04")),
    (D("11700"), D("0.045")),
    (D("13900"), D("0.0525")),
    (D("80650"), D("0.055")),
    (D("215400"), D("0.06")),
    (D("1077550"), D("0.0685")),
    (D("5000000"), D("0.0965")),
    (D("25000000"), D("0.103")),
    (None, D("0.109")),
]

_MFJ = [
    (D("17150"), D("0.04")),
    (D("23600"), D("0.045")),
    (D("27900"), D("0.0525")),
    (D("161550"), D("0.055")),
    (D("323200"), D("0.06")),
    (D("2155350"), D("0.0685")),
    (D("5000000"), D("0.0965")),
    (D("25000000"), D("0.103")),
    (None, D("0.109")),
]

_HOH = [
    (D("12800"), D("0.04")),
    (D("17650"), D("0.045")),
    (D("20900"), D("0.0525")),
    (D("107650"), D("0.055")),
    (D("269300"), D("0.06")),
    (D("1616450"), D("0.0685")),
    (D("5000000"), D("0.0965")),
    (D("25000000"), D("0.103")),
    (None, D("0.109")),
]

PACK = register(
    BracketStatePack(
        state="NY",
        year=2025,
        source="N.Y. Tax Law 601; NY DTF rate schedules + standard deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("8000"),
            FilingStatus.MARRIED_SEPARATELY: D("8000"),
            FilingStatus.MARRIED_JOINTLY: D("16050"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("11200"),
        },
    )
)
