"""Arkansas individual income tax, 2025 (flat-rate approximation).

Arkansas uses several rate schedules that vary by income level plus a "bracket
adjustment" (a phase-in of the top rate), and the middle marginal rate has at
times exceeded the top rate -- a non-monotonic structure the bracket-pack model
cannot represent. As a documented approximation this pack applies the **top rate
of 3.9%** (the 2024 enacted rate) as effectively flat on federal AGI. This
materially overstates tax for low-income filers, who face the graduated low-rate
tables; a maintainer should replace this with a faithful schedule.

Sources:
  * Ark. Code 26-51-201 (individual income tax rates).
  * Arkansas DFA 2024 top rate 3.9%.

``verified=False``: rate transcribed from the cited summary and the structure
is deliberately simplified; not reconciled against the published 2025 AR1000F.
"""

from decimal import Decimal

from app.state_rules.base import FEDERAL_AGI, FlatStatePack
from app.state_rules.registry import register

PACK = register(
    FlatStatePack(
        state="AR",
        year=2025,
        source="Ark. Code 26-51-201; AR DFA 2024 top rate 3.9% (approx as flat)",
        verified=False,
        rate=Decimal("0.039"),
        base=FEDERAL_AGI,
    )
)
