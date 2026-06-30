"""New Hampshire Interest & Dividends Tax (narrow-base reference pack).

New Hampshire has no tax on wages. It historically taxed only interest and
dividend income (the I&D Tax) above a per-filer exemption. That tax was phased
out and is **fully repealed effective January 1, 2025**, so the 2025 rate is 0%.

This pack exists to exercise the custom-``compute`` code path for states whose
base is not ordinary income, and to make the repeal explicit in the trace rather
than silently returning zero. ``rate`` is kept as a parameter so the same class
can model the phase-down years (5% -> 4% -> 3% -> 0%).

Sources:
  * N.H. RSA 77 (Interest & Dividends Tax).
  * HB 2 (2023), accelerating repeal to tax periods beginning after 2024.

``verified=False``: repeal/exemption transcribed from the cited summary, not yet
reconciled against the published NH DRA guidance in this environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.schemas import FilingStatus, TaxpayerData
from app.state_rules.base import FederalContext, StateResult
from app.state_rules.registry import register

ZERO = Decimal("0")


@dataclass(frozen=True)
class NewHampshireIDPack:
    """Taxes interest + dividends above an exemption; nothing else."""

    state: str = "NH"
    year: int = 2025
    source: str = "N.H. RSA 77; HB 2 (2023) full repeal effective 2025-01-01"
    verified: bool = False
    rate: Decimal = ZERO  # I&D Tax repealed for 2025
    exemption_unmarried: Decimal = Decimal("2400")
    exemption_joint: Decimal = Decimal("4800")

    def compute(self, data: TaxpayerData, federal: FederalContext) -> StateResult:
        investment_income = data.taxable_interest + data.ordinary_dividends
        exemption = (
            self.exemption_joint
            if federal.filing_status == FilingStatus.MARRIED_JOINTLY
            else self.exemption_unmarried
        )
        base = max(ZERO, investment_income - exemption)
        tax = (base * self.rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        note = " (I&D Tax repealed effective 2025)" if self.rate == ZERO else ""
        trace = [
            f"NH: interest+dividends {investment_income} - exemption "
            f"{exemption} = {base}; rate {self.rate} -> {tax}{note}"
        ]
        return StateResult("NH", base, tax, trace)


PACK = register(NewHampshireIDPack())
