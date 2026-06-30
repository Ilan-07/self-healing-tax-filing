"""California individual income tax (progressive-bracket reference pack).

California's return uses its own nine-bracket schedule (1%-12.3%) and a state
standard deduction. As a documented approximation this pack starts from federal
AGI; a fully accurate CA return would recompute CA AGI with state-specific
add-backs/subtractions. The extra 1% Mental Health Services Tax on income over
$1,000,000 is *not* modeled here.

Sources:
  * Cal. Rev. & Tax. Code sec. 17041 (rate schedule).
  * California FTB tax-rate schedules and standard deduction (2024 tax year,
    indexed annually).

``verified=False``: brackets and standard deduction transcribed from the FTB
2024-indexed schedules pending publication/reconciliation of the 2025 figures.
Labeled ``year=2025`` to pair with the 2025 federal pack; a maintainer must
reconcile against the published 2025 CA schedule before flipping ``verified``.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("10756"), D("0.01")),
    (D("25499"), D("0.02")),
    (D("40245"), D("0.04")),
    (D("55866"), D("0.06")),
    (D("70606"), D("0.08")),
    (D("360659"), D("0.093")),
    (D("432787"), D("0.103")),
    (D("721314"), D("0.113")),
    (None, D("0.123")),
]

_MFJ = [
    (D("21512"), D("0.01")),
    (D("50998"), D("0.02")),
    (D("80490"), D("0.04")),
    (D("111732"), D("0.06")),
    (D("141212"), D("0.08")),
    (D("721318"), D("0.093")),
    (D("865574"), D("0.103")),
    (D("1442628"), D("0.113")),
    (None, D("0.123")),
]

_HOH = [
    (D("21527"), D("0.01")),
    (D("51000"), D("0.02")),
    (D("65744"), D("0.04")),
    (D("81364"), D("0.06")),
    (D("96107"), D("0.08")),
    (D("490493"), D("0.093")),
    (D("588593"), D("0.103")),
    (D("980987"), D("0.113")),
    (None, D("0.123")),
]

PACK = register(
    BracketStatePack(
        state="CA",
        year=2025,
        source="Cal. R&TC 17041; CA FTB 2024-indexed rate schedules",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("5540"),
            FilingStatus.MARRIED_SEPARATELY: D("5540"),
            FilingStatus.MARRIED_JOINTLY: D("11080"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("11080"),
        },
    )
)
