"""North Dakota individual income tax, 2025 (progressive-bracket reference pack).

North Dakota's 2023 reform left a three-band schedule with a 0% bottom bracket
and a 2.5% top rate, tied to federal taxable income; this pack uses
``base=federal_taxable_income`` with separate Single and MFJ edges. North
Dakota's own adjustments are not modeled.

Sources:
  * N.D.C.C. 57-38-30.3 (individual income tax rates); S.B. 2274 (2023).
  * North Dakota OSTC 2024-indexed brackets.

``verified=False``: brackets transcribed from the 2024-indexed tables, not yet
reconciled against the published 2025 ND Form ND-1.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("47150"), D("0")),
    (D("238200"), D("0.0195")),
    (None, D("0.025")),
]

_MFJ = [
    (D("79200"), D("0")),
    (D("289975"), D("0.0195")),
    (None, D("0.025")),
]

PACK = register(
    BracketStatePack(
        state="ND",
        year=2025,
        source="N.D.C.C. 57-38-30.3; S.B. 2274 (2023); ND OSTC 2024 brackets",
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
