"""New Mexico individual income tax, 2025 (progressive-bracket reference pack).

New Mexico's five-band schedule tops out at 5.9% with doubled-ish bracket edges
for MFJ. New Mexico allows the federal standard deduction, so this pack uses
``base=federal_taxable_income``. New Mexico's low-income comprehensive tax rebate
and exemptions are not modeled.

NOTE: HB 252 (2024) restructured the brackets effective tax year 2025; this pack
still encodes the prior (2024) schedule pending confirmation of the new edges.

Sources:
  * N.M. Stat. 7-2-7 (individual income tax rates).
  * New Mexico TRD 2024 rate schedules.

``verified=False``: brackets transcribed from the 2024 schedule, not yet
reconciled against the HB 252 2025 schedule / published PIT-1.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("5500"), D("0.017")),
    (D("11000"), D("0.032")),
    (D("16000"), D("0.047")),
    (D("210000"), D("0.049")),
    (None, D("0.059")),
]

_MFJ = [
    (D("8000"), D("0.017")),
    (D("16000"), D("0.032")),
    (D("24000"), D("0.047")),
    (D("315000"), D("0.049")),
    (None, D("0.059")),
]

PACK = register(
    BracketStatePack(
        state="NM",
        year=2025,
        source="N.M. Stat. 7-2-7; NM TRD 2024 rate schedules (pre-HB 252)",
        verified=False,
        base=FEDERAL_TAXABLE_INCOME,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
        },
    )
)
