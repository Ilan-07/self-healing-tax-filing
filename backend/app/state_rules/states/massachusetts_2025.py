"""Massachusetts individual income tax, 2025 (reference pack).

Massachusetts taxes most income at a flat 5.0%, plus a 4% "Fair Share" surtax
on the portion of taxable income above an annually indexed threshold
($1,083,150 for 2025). That is naturally a two-band schedule (5% then 9%),
identical across filing statuses (the threshold is per return). Applied to
federal AGI as a documented approximation; Massachusetts's separate treatment of
short-term gains and its own deductions/exemptions are not modeled.

Sources:
  * Mass. Gen. Laws ch. 62 sec. 4 (5.0% Part B rate).
  * Mass. Const. amend. art. 44 ("Fair Share") 4% surtax; DOR 2025 threshold
    $1,083,150.

``verified=False``: rate and surtax threshold transcribed from the cited
summaries, not yet reconciled against the published 2025 MA Form 1.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.state_rules.base import FEDERAL_AGI, BracketStatePack
from app.state_rules.registry import register

_SCHEDULE = [
    (Decimal("1083150"), Decimal("0.05")),
    (None, Decimal("0.09")),
]

PACK = register(
    BracketStatePack(
        state="MA",
        year=2025,
        source="M.G.L. ch. 62 s.4; art. 44 surtax 4% over $1,083,150 (2025)",
        verified=False,
        base=FEDERAL_AGI,
        brackets={
            FilingStatus.SINGLE: _SCHEDULE,
            FilingStatus.MARRIED_SEPARATELY: _SCHEDULE,
            FilingStatus.MARRIED_JOINTLY: _SCHEDULE,
            FilingStatus.HEAD_OF_HOUSEHOLD: _SCHEDULE,
        },
    )
)
