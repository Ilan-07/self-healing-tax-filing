"""High-accuracy state tax via the ``tenforty`` library (OpenTaxSolver engine).

For states where we want close-to-return accuracy, we delegate the state
computation to ``tenforty`` rather than our hand-encoded bracket packs. tenforty
computes the state's own taxable-income base, deductions, exemptions, and
credits, which our reference packs deliberately approximate.

A :class:`TenfortyStatePack` is a drop-in :class:`StateRulePack`: it maps our
``TaxpayerData`` onto tenforty's inputs, takes ``state_total_tax``, and -- so the
pipeline can never fail on an external-engine hiccup or a missing dependency --
falls back to a supplied reference pack on any error.

Per-state income routing. OTS's per-state forms interpret tenforty's generic
income fields inconsistently. CA/NY/AZ tax every field correctly. NJ's form is
buggy: it *ignores* long-term capital gains and *fully excludes* Schedule-1
income (regardless of age/income limits). So NJ uses a dedicated router
(:func:`nj_income_kwargs`) that funnels NJ-taxable income into the fields OTS-NJ
does tax and applies NJ's statutory retirement exclusions itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.schemas import FilingStatus, TaxpayerData
from app.state_rules.base import FederalContext, StateResult, StateRulePack

ZERO = Decimal("0")

try:  # tenforty is an optional-at-runtime dependency; degrade gracefully.
    from tenforty import evaluate_return
except Exception:  # pragma: no cover - exercised only when the wheel is absent
    evaluate_return = None  # type: ignore[assignment]


# Our filing statuses -> tenforty's OTSFilingStatus strings. QSS is mapped to
# MFJ by the federal engine before a pack ever runs, but it is handled here too.
_FILING_STATUS = {
    FilingStatus.SINGLE: "Single",
    FilingStatus.MARRIED_JOINTLY: "Married/Joint",
    FilingStatus.MARRIED_SEPARATELY: "Married/Sep",
    FilingStatus.HEAD_OF_HOUSEHOLD: "Head_of_House",
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: "Widow(er)",
}

# TaxpayerData + FederalContext -> tenforty income kwargs.
IncomeRouter = Callable[[TaxpayerData, FederalContext], dict]
# TaxpayerData -> excludable pension amount.
PensionExclusion = Callable[[TaxpayerData], Decimal]


# --- Age eligibility ---------------------------------------------------------
# Prefer exact age at the tax year-end (from date of birth), then the integer
# ``age`` field, then the 65+ booleans. This captures boundaries like NY's 59.5
# and NJ's "62 by year-end" precisely when a birth date is supplied.

def _filer_meets(
    birth: date | None, age: int, flag_65: bool, threshold: float, year: int
) -> bool:
    if birth is not None:
        return (date(year, 12, 31) - birth).days / 365.25 >= threshold
    if age:
        return age >= threshold
    return flag_65 and threshold <= 65


def _eligible_filers_at_least(data: TaxpayerData, threshold: float) -> int:
    """Count filers (spouse only for MFJ) known to meet an age threshold."""
    count = 1 if _filer_meets(
        data.birth_date, data.age, data.age_65_plus, threshold, data.tax_year
    ) else 0
    if data.filing_status == FilingStatus.MARRIED_JOINTLY and _filer_meets(
        data.spouse_birth_date,
        data.spouse_age,
        data.spouse_65_plus,
        threshold,
        data.tax_year,
    ):
        count += 1
    return count


def _net_capital_gain(data: TaxpayerData) -> Decimal:
    return max(ZERO, data.long_term_capital_gain + data.short_term_capital_gain)


# --- Pension exclusions ------------------------------------------------------

def ny_pension_exclusion(data: TaxpayerData) -> Decimal:
    """N.Y. Tax Law 612(c)(3-a): up to $20,000 of pension/annuity income per
    individual who is 59.5+ (exact when a birth date is given; otherwise age>=60
    as a never-over-exclude proxy, then the 65+ flag)."""
    pension = data.taxable_pension_ira
    if pension <= 0:
        return ZERO
    return min(pension, Decimal("20000") * _eligible_filers_at_least(data, 59.5))


# NJ retirement-income exclusion caps by filing status (gross income <= $100k).
_NJ_CAP = {
    FilingStatus.MARRIED_JOINTLY: Decimal("100000"),
    FilingStatus.MARRIED_SEPARATELY: Decimal("50000"),
}
_NJ_CAP_DEFAULT = Decimal("75000")  # single / HoH / QSS


def _nj_exclusions(data: TaxpayerData) -> tuple[Decimal, Decimal]:
    """N.J.S.A. 54A:6-10/6-15. Returns (pension exclusion, other-retirement
    exclusion). Requires a filer 62+ and NJ gross income <= $150k; the cap is
    phased 100%/50%/25% across the $100k/$125k/$150k bands. The Other Retirement
    Income Exclusion lets filers with earned income <= $3,000 apply the *unused*
    cap to non-pension income too.
    """
    pension = data.taxable_pension_ira
    if _eligible_filers_at_least(data, 62) == 0:
        return ZERO, ZERO
    ncg = _net_capital_gain(data)
    earned = data.wages + data.partnership_income + data.self_employment_income
    gross = (
        earned
        + data.other_income
        + pension
        + data.taxable_interest
        + data.ordinary_dividends
        + ncg
    )
    if gross > Decimal("150000"):
        return ZERO, ZERO
    cap = _NJ_CAP.get(data.filing_status, _NJ_CAP_DEFAULT)
    if gross > Decimal("125000"):
        cap *= Decimal("0.25")
    elif gross > Decimal("100000"):
        cap *= Decimal("0.50")
    pension_excl = min(pension, cap)
    orie = ZERO
    if earned <= Decimal("3000"):
        nonearned_other = (
            data.other_income + data.taxable_interest + data.ordinary_dividends + ncg
        )
        orie = min(nonearned_other, cap - pension_excl)
    return pension_excl, orie


# --- Income routers ----------------------------------------------------------

def default_income_kwargs(
    data: TaxpayerData,
    federal: FederalContext,
    *,
    pension_exclusion: PensionExclusion | None = None,
    taxes_social_security: bool = False,
) -> dict:
    """CA/NY/AZ: every income field is taxed correctly by OTS. Pension/IRA,
    partnership, and other income go to Schedule 1; an optional state pension
    exclusion (NY) reduces the taxable pension; SS is injected only if taxed."""
    excluded = pension_exclusion(data) if pension_exclusion else ZERO
    taxable_pension = max(ZERO, data.taxable_pension_ira - excluded)
    schedule_1 = data.partnership_income + data.other_income + taxable_pension
    if taxes_social_security:
        schedule_1 += federal.taxable_social_security
    return dict(
        w2_income=float(data.wages),
        taxable_interest=float(data.taxable_interest),
        ordinary_dividends=float(data.ordinary_dividends),
        qualified_dividends=float(data.qualified_dividends),
        short_term_capital_gains=float(data.short_term_capital_gain),
        long_term_capital_gains=float(data.long_term_capital_gain),
        self_employment_income=float(data.self_employment_income),
        schedule_1_income=float(schedule_1),
    )


def nj_income_kwargs(data: TaxpayerData, federal: FederalContext) -> dict:
    """NJ: OTS ignores LTCG and excludes Schedule-1 income, so route NJ-taxable
    income into fields it does tax. Actual W-2 wages (plus partnership/SE earned
    income) stay in ``w2_income`` to preserve earned-income fidelity for NJ's
    EITC; all other NJ-taxable ordinary income (pension after exclusion,
    interest, dividends, net capital gain, other) is summed into
    ``ordinary_dividends`` (taxed as ordinary, non-earned). NJ's pension and
    Other Retirement Income exclusions are applied here. SS is never NJ-taxable.
    """
    pension_excl, orie = _nj_exclusions(data)
    taxable_pension = max(ZERO, data.taxable_pension_ira - pension_excl)
    nonearned = (
        taxable_pension
        + data.other_income
        + data.taxable_interest
        + data.ordinary_dividends
        + _net_capital_gain(data)
    )
    nonearned_taxable = max(ZERO, nonearned - orie)
    earned = data.wages + data.partnership_income + data.self_employment_income
    return dict(
        w2_income=float(earned),
        ordinary_dividends=float(nonearned_taxable),
        taxable_interest=0.0,
        qualified_dividends=0.0,
        short_term_capital_gains=0.0,
        long_term_capital_gains=0.0,
        self_employment_income=0.0,
        schedule_1_income=0.0,
    )


@dataclass(frozen=True)
class TenfortyStatePack:
    """Delegates state tax to ``tenforty``; falls back to a reference pack.

    Income mapping is done by ``income_router`` (defaults to
    :func:`default_income_kwargs` with ``pension_exclusion``/
    ``taxes_social_security``). NJ supplies :func:`nj_income_kwargs`. Social
    Security is injected only for states flagged ``taxes_social_security`` (none
    of CA/NY/NJ/AZ tax it). Itemize/standard is a best-effort heuristic.
    """

    state: str
    year: int
    source: str
    verified: bool
    fallback: StateRulePack
    taxes_social_security: bool = False
    pension_exclusion: PensionExclusion | None = None
    income_router: IncomeRouter | None = None

    def _kwargs(self, data: TaxpayerData, federal: FederalContext) -> dict:
        sch_a = (
            data.salt_paid
            + data.mortgage_interest
            + data.medical_expenses
            + data.charitable_contributions
        )
        itemized = data.itemized_deductions if data.itemized_deductions > 0 else sch_a
        if self.income_router is not None:
            income = self.income_router(data, federal)
        else:
            income = default_income_kwargs(
                data,
                federal,
                pension_exclusion=self.pension_exclusion,
                taxes_social_security=self.taxes_social_security,
            )
        kwargs: dict = dict(
            year=data.tax_year,
            state=self.state,
            filing_status=_FILING_STATUS.get(data.filing_status, "Single"),
            num_dependents=data.qualifying_children + data.other_dependents,
            **income,
        )
        if itemized > 0:
            kwargs["standard_or_itemized"] = "Itemized"
            kwargs["itemized_deductions"] = float(itemized)
        return kwargs

    def compute(self, data: TaxpayerData, federal: FederalContext) -> StateResult:
        if evaluate_return is None:
            return self._fallback(data, federal, "tenforty not installed")
        try:
            result = evaluate_return(on_error="raise", **self._kwargs(data, federal))
            tax = Decimal(str(result.state_total_tax or 0))
            sti = Decimal(str(result.state_taxable_income or 0))
        except Exception as exc:  # pragma: no cover - defensive
            return self._fallback(data, federal, f"tenforty error: {exc}")
        trace = [
            f"{self.state}: tenforty {self.year} -> state tax {tax} "
            f"(state taxable income {sti})"
        ]
        return StateResult(self.state, sti, tax, trace)

    def _fallback(
        self, data: TaxpayerData, federal: FederalContext, reason: str
    ) -> StateResult:
        result = self.fallback.compute(data, federal)
        return StateResult(
            result.state,
            result.state_taxable_income,
            result.tax,
            [f"{self.state}: fell back to reference pack ({reason})", *result.trace],
        )
