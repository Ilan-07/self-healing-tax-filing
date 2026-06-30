"""Connecticut individual income tax (progressive-bracket reference pack).

Connecticut's seven-band schedule (2% / 4.5% / 5.5% / 6% / 6.5% / 6.9% / 6.99%)
uses separate bracket edges for Single/MFS, MFJ, and HOH. Applied to federal AGI
as a documented approximation.

Connecticut's personal exemption (which phases out as income rises) and its 3%
tax-rate "recapture" / benefit-recapture provisions are **not modeled**.

Sources:
  * Conn. Gen. Stat. 12-700 (individual income tax rate schedule).
  * Connecticut DRS 2024 rate schedules (post-2024 rate cut to 2% / 4.5%).

``verified=False``: brackets transcribed from the cited schedules, not yet
reconciled against the published 2025 CT-1040.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

D = Decimal

# Single and Married Filing Separately.
_SINGLE = [
    (D("10000"), D("0.02")),
    (D("50000"), D("0.045")),
    (D("100000"), D("0.055")),
    (D("200000"), D("0.06")),
    (D("250000"), D("0.065")),
    (D("500000"), D("0.069")),
    (None, D("0.0699")),
]

# Married Filing Jointly.
_MFJ = [
    (D("20000"), D("0.02")),
    (D("100000"), D("0.045")),
    (D("200000"), D("0.055")),
    (D("400000"), D("0.06")),
    (D("500000"), D("0.065")),
    (D("1000000"), D("0.069")),
    (None, D("0.0699")),
]

# Head of Household.
_HOH = [
    (D("16000"), D("0.02")),
    (D("80000"), D("0.045")),
    (D("160000"), D("0.055")),
    (D("320000"), D("0.06")),
    (D("400000"), D("0.065")),
    (D("800000"), D("0.069")),
    (None, D("0.0699")),
]

PACK = register(
    BracketStatePack(
        state="CT",
        year=2025,
        source="Conn. Gen. Stat. 12-700; CT DRS 2024 rate schedules",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SINGLE,
            FilingStatus.MARRIED_SEPARATELY: _SINGLE,
            FilingStatus.MARRIED_JOINTLY: _MFJ,
            FilingStatus.HEAD_OF_HOUSEHOLD: _HOH,
        },
    )
)
