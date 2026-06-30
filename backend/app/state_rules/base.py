"""Per-state income-tax rule packs.

A *rule pack* is the state-level peer of a federal ``TaxYearParams``: it models
one state's income tax for one year and carries its own provenance (``source`` +
``verified``), the same contract enforced on the federal side. The same rule
applies here: constants must never be invented -- every number must be traceable
to the state's published schedule (or a citeable summary) so a reviewer can
confirm it is current. ``verified=False`` means "transcribed but not yet
reconciled against the published source in this environment."

Three shapes cover the landscape of 40+ taxing states:

* :class:`FlatStatePack`    -- a single rate (CO, IL, PA, UT, ...).
* :class:`BracketStatePack` -- progressive brackets (CA, NY, NJ, MN, ...).
* a custom class implementing :class:`StateRulePack` for the oddballs whose base
  is not ordinary income (NH interest/dividends, WA capital gains).

States with no income tax (AK, FL, NV, SD, TX, WY, TN) simply have no pack
installed; :func:`app.state_rules.get_state_pack` returns ``None`` and the
engine falls back to the (default-zero) flat ``state_tax_rate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol, runtime_checkable

from app.schemas import FilingStatus, TaxpayerData
from app.tax_rules.params import Bracket, progressive_tax

ZERO = Decimal("0")
DOLLAR = Decimal("1")

# Which federal line a state return starts from. Most states begin at federal
# AGI (then apply their own deductions); a few start at federal taxable income.
FEDERAL_AGI = "federal_agi"
FEDERAL_TAXABLE_INCOME = "federal_taxable_income"


def _dollars(value: Decimal) -> Decimal:
    return Decimal(value).quantize(DOLLAR, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FederalContext:
    """The federal results a state pack needs as its starting point.

    ``filing_status`` is already normalized by the federal engine (QSS has been
    mapped to MFJ), so packs only ever see SINGLE / MFJ / MFS / HOH.
    """

    filing_status: FilingStatus
    agi: Decimal
    taxable_income: Decimal
    taxable_social_security: Decimal = ZERO


@dataclass(frozen=True)
class StateResult:
    state: str
    state_taxable_income: Decimal
    tax: Decimal
    trace: list[str] = field(default_factory=list)


@runtime_checkable
class StateRulePack(Protocol):
    """One state's income-tax rules for one year."""

    state: str  # USPS code, e.g. "CA"
    year: int
    source: str
    verified: bool

    def compute(self, data: TaxpayerData, federal: FederalContext) -> StateResult:
        ...


def _starting_income(base: str, federal: FederalContext) -> Decimal:
    if base == FEDERAL_TAXABLE_INCOME:
        return federal.taxable_income
    return federal.agi


@dataclass(frozen=True)
class FlatStatePack:
    """A state with a single flat rate (e.g. Colorado 4.40%)."""

    state: str
    year: int
    source: str
    verified: bool
    rate: Decimal
    base: str = FEDERAL_TAXABLE_INCOME
    standard_deduction: dict[FilingStatus, Decimal] = field(default_factory=dict)

    def compute(self, data: TaxpayerData, federal: FederalContext) -> StateResult:
        start = _starting_income(self.base, federal)
        std = self.standard_deduction.get(federal.filing_status, ZERO)
        sti = max(ZERO, _dollars(start - std))
        tax = _dollars(sti * self.rate)
        trace = [
            f"{self.state}: {self.base} {start} - std {std} = {sti}; "
            f"flat {self.rate} -> {tax}"
        ]
        return StateResult(self.state, sti, tax, trace)


@dataclass(frozen=True)
class BracketStatePack:
    """A state with progressive brackets (e.g. California).

    ``brackets`` must cover SINGLE, MFJ, MFS and HOH (validation enforces this).
    Both ``standard_deduction`` and ``personal_exemption`` are optional, since
    many states use one, the other, or neither.
    """

    state: str
    year: int
    source: str
    verified: bool
    brackets: dict[FilingStatus, list[Bracket]]
    base: str = FEDERAL_AGI
    standard_deduction: dict[FilingStatus, Decimal] = field(default_factory=dict)
    personal_exemption: dict[FilingStatus, Decimal] = field(default_factory=dict)

    def compute(self, data: TaxpayerData, federal: FederalContext) -> StateResult:
        fs = federal.filing_status
        start = _starting_income(self.base, federal)
        std = self.standard_deduction.get(fs, ZERO)
        exemption = self.personal_exemption.get(fs, ZERO)
        sti = max(ZERO, _dollars(start - std - exemption))
        tax = _dollars(progressive_tax(sti, self.brackets[fs]))
        trace = [
            f"{self.state}: {self.base} {start} - std {std} - exemption "
            f"{exemption} = {sti}; brackets -> {tax}"
        ]
        return StateResult(self.state, sti, tax, trace)
