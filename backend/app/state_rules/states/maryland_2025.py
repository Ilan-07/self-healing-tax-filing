"""Maryland individual income tax, 2025 (progressive-bracket reference pack).

Maryland's eight-band state schedule (2% to 5.75%) uses different bracket edges
for Single/MFS than for MFJ/HOH/QSS. **State tax only** -- Maryland's county
"piggyback" income taxes (roughly 2.25%-3.2%) are out of scope here.

Maryland's standard deduction is 15% of Maryland AGI bounded by a min/max; this
pack applies the maximum ($2,700 single / $5,450 MFJ) to federal AGI as a
documented approximation. That is accurate above roughly $18k (single) / $36k
(MFJ) of AGI, where 15% exceeds the cap; lower-income filers are overstated.
Personal exemptions are not modeled.

Sources:
  * Md. Code, Tax-Gen. 10-105 (state rate schedule).
  * Comptroller of Maryland 2025 standard deduction min/max.

``verified=False``: brackets and standard deduction transcribed from the cited
summaries, not yet reconciled against the published 2025 MD Form 502.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

# Single and Married Filing Separately.
_SINGLE = [
    (D("1000"), D("0.02")),
    (D("2000"), D("0.03")),
    (D("3000"), D("0.04")),
    (D("100000"), D("0.0475")),
    (D("125000"), D("0.05")),
    (D("150000"), D("0.0525")),
    (D("250000"), D("0.055")),
    (None, D("0.0575")),
]

# Married Filing Jointly, Head of Household, Qualifying Surviving Spouse.
_JOINT = [
    (D("1000"), D("0.02")),
    (D("2000"), D("0.03")),
    (D("3000"), D("0.04")),
    (D("150000"), D("0.0475")),
    (D("175000"), D("0.05")),
    (D("225000"), D("0.0525")),
    (D("300000"), D("0.055")),
    (None, D("0.0575")),
]

PACK = register(
    BracketStatePack(
        state="MD",
        year=2025,
        source="Md. Code Tax-Gen. 10-105; Comptroller of MD 2025 std deduction",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _JOINT,
            FilingStatus.HEAD_OF_HOUSEHOLD: _JOINT,
        },
        standard_deduction={
            FilingStatus.SINGLE: D("2700"),
            FilingStatus.MARRIED_SEPARATELY: D("2700"),
            FilingStatus.MARRIED_JOINTLY: D("5450"),
            FilingStatus.HEAD_OF_HOUSEHOLD: D("5450"),
        },
    )
)
