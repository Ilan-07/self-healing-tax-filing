"""California individual income tax (progressive-bracket reference pack).

California uses a nine-bracket schedule (1%-12.3%) and a state standard
deduction. As a documented approximation this pack starts from federal AGI; a
fully accurate CA return recomputes CA AGI with state-specific
add-backs/subtractions, and the exemption credits and the 1% Mental Health
Services Tax over $1,000,000 are not modeled here.

In production CA is served by the high-accuracy ``tenforty`` pack (see
``_tenforty_overrides``); this reference pack is the crash-proof fallback.

Sources:
  * Cal. Rev. & Tax. Code sec. 17041 (rate schedule).
  * FTB 2025 California Tax Rate Schedules and standard deduction
    (single/MFS $5,706; MFJ/HoH/QSS $11,412). Bracket edges and standard
    deduction reconciled against the published 2025 FTB schedules (2026-07).

``verified=False``: the *parameters* match the official 2025 FTB schedules, but
this simplified model omits the exemption credits and the $1M surtax, so it is
not return-accurate -- use the tenforty pack for that.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

_SINGLE = [
    (D("11079"), D("0.01")),
    (D("26264"), D("0.02")),
    (D("41452"), D("0.04")),
    (D("57542"), D("0.06")),
    (D("72724"), D("0.08")),
    (D("371479"), D("0.093")),
    (D("445771"), D("0.103")),
    (D("742953"), D("0.113")),
    (None, D("0.123")),
]

_MFJ = [
    (D("22158"), D("0.01")),
    (D("52528"), D("0.02")),
    (D("82904"), D("0.04")),
    (D("115084"), D("0.06")),
    (D("145448"), D("0.08")),
    (D("742958"), D("0.093")),
    (D("891542"), D("0.103")),
    (D("1485906"), D("0.113")),
    (None, D("0.123")),
]

_HOH = [
    (D("22173"), D("0.01")),
    (D("52530"), D("0.02")),
    (D("67716"), D("0.04")),
    (D("83805"), D("0.06")),
    (D("98990"), D("0.08")),
    (D("505208"), D("0.093")),
    (D("606251"), D("0.103")),
    (D("1010417"), D("0.113")),
    (None, D("0.123")),
]

PACK = register(
    BracketStatePack(
        state="CA",
        year=2025,
        source="Cal. R&TC 17041; FTB 2025 rate schedules (verified 2026-07)",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("5706"),
            FilingStatus.MARRIED_SEPARATELY: D("5706"),
            FilingStatus.MARRIED_JOINTLY: D("11412"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("11412"),
        },
    )
)
