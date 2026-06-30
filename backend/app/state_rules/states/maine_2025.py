"""Maine individual income tax, 2025 (progressive-bracket reference pack).

Maine's three-band schedule (5.8% / 6.75% / 7.15%) uses separate bracket edges
for Single, MFJ, and HOH. Maine's standard deduction tracks the federal amount,
so Maine taxable income begins at federal taxable income; this pack uses
``base=federal_taxable_income``. Maine's personal exemption and credits are not
modeled.

Sources:
  * 36 M.R.S. 5111 (individual income tax rate schedule).
  * Maine Revenue Services 2024-indexed brackets.

``verified=False``: brackets transcribed from the 2024-indexed tables, not yet
reconciled against the published 2025 ME Form 1040ME.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("26050"), D("0.058")),
    (D("61600"), D("0.0675")),
    (None, D("0.0715")),
]

_MFJ = [
    (D("52100"), D("0.058")),
    (D("123250"), D("0.0675")),
    (None, D("0.0715")),
]

_HOH = [
    (D("39050"), D("0.058")),
    (D("92450"), D("0.0675")),
    (None, D("0.0715")),
]

PACK = register(
    BracketStatePack(
        state="ME",
        year=2025,
        source="36 M.R.S. 5111; Maine Revenue Services 2024-indexed brackets",
        verified=False,
        base=FEDERAL_TAXABLE_INCOME,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
    )
)
