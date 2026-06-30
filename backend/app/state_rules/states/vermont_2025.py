"""Vermont individual income tax, 2025 (progressive-bracket reference pack).

Vermont's four-band schedule (3.35% / 6.6% / 7.6% / 8.75%) uses separate bracket
edges for Single, MFJ, and HOH and is tied to Vermont taxable income, which
begins at federal taxable income; this pack uses ``base=federal_taxable_income``.
Vermont's exemptions and credits are not modeled.

Sources:
  * 32 V.S.A. 5822 (individual income tax rate schedule).
  * Vermont Dept. of Taxes 2024-indexed brackets.

``verified=False``: brackets transcribed from the 2024-indexed tables, not yet
reconciled against the published 2025 VT Form IN-111.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_TAXABLE_INCOME, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("45400"), D("0.0335")),
    (D("110050"), D("0.066")),
    (D("229550"), D("0.076")),
    (None, D("0.0875")),
]

_MFJ = [
    (D("75850"), D("0.0335")),
    (D("183400"), D("0.066")),
    (D("279450"), D("0.076")),
    (None, D("0.0875")),
]

_HOH = [
    (D("60850"), D("0.0335")),
    (D("157150"), D("0.066")),
    (D("254500"), D("0.076")),
    (None, D("0.0875")),
]

PACK = register(
    BracketStatePack(
        state="VT",
        year=2025,
        source="32 V.S.A. 5822; Vermont Dept. of Taxes 2024-indexed brackets",
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
