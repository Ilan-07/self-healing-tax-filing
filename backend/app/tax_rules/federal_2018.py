"""Federal tax parameters for tax year 2018.

Sources (verify before flipping ``verified=True``):
  * Rev. Proc. 2018-18 (2018 inflation adjustments).
  * Tax Cuts and Jobs Act (TCJA): $2,000 Child Tax Credit, $500 ODC.
  * SSA 2018 OASDI wage base = $128,400.

Retained mainly to exercise the multi-year parameter registry.
``verified=False``.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.tax_rules.params import (
    CreditParams,
    PreferentialRates,
    TaxYearParams,
    register,
)


STANDARD_DEDUCTIONS = {
    FilingStatus.SINGLE: Decimal("12000"),
    FilingStatus.MARRIED_JOINTLY: Decimal("24000"),
    FilingStatus.MARRIED_SEPARATELY: Decimal("12000"),
    FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("18000"),
}

BRACKETS = {
    FilingStatus.SINGLE: [
        (Decimal("9525"), Decimal("0.10")),
        (Decimal("38700"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("500000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_JOINTLY: [
        (Decimal("19050"), Decimal("0.10")),
        (Decimal("77400"), Decimal("0.12")),
        (Decimal("165000"), Decimal("0.22")),
        (Decimal("315000"), Decimal("0.24")),
        (Decimal("400000"), Decimal("0.32")),
        (Decimal("600000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_SEPARATELY: [
        (Decimal("9525"), Decimal("0.10")),
        (Decimal("38700"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("300000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (Decimal("13600"), Decimal("0.10")),
        (Decimal("51800"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("500000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
}

PARAMS = register(
    TaxYearParams(
        year=2018,
        source="Rev. Proc. 2018-18; TCJA; SSA 2018",
        verified=False,
        standard_deductions=STANDARD_DEDUCTIONS,
        additional_std_married=Decimal("1300"),
        additional_std_unmarried=Decimal("1600"),
        brackets=BRACKETS,
        preferential=PreferentialRates(
            zero_rate_max={
                FilingStatus.SINGLE: Decimal("38600"),
                FilingStatus.MARRIED_JOINTLY: Decimal("77200"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("38600"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("51700"),
            },
            fifteen_rate_max={
                FilingStatus.SINGLE: Decimal("425800"),
                FilingStatus.MARRIED_JOINTLY: Decimal("479000"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("239500"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("452400"),
            },
        ),
        credits=CreditParams(
            ctc_per_child=Decimal("2000"),
            ctc_refundable_cap=Decimal("1400"),
            odc_per_dependent=Decimal("500"),
            phaseout_start={
                FilingStatus.SINGLE: Decimal("200000"),
                FilingStatus.MARRIED_JOINTLY: Decimal("400000"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("200000"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("200000"),
            },
            phaseout_per_1000=Decimal("50"),
        ),
        ss_wage_base=Decimal("128400"),
        ss_rate=Decimal("0.062"),
        medicare_rate=Decimal("0.0145"),
        addl_medicare_rate=Decimal("0.009"),
        addl_medicare_threshold={
            FilingStatus.SINGLE: Decimal("200000"),
            FilingStatus.MARRIED_JOINTLY: Decimal("250000"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("125000"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("200000"),
        },
        niit_rate=Decimal("0.038"),
        niit_threshold={
            FilingStatus.SINGLE: Decimal("200000"),
            FilingStatus.MARRIED_JOINTLY: Decimal("250000"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("125000"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("200000"),
        },
        se_net_factor=Decimal("0.9235"),
        se_combined_rate=Decimal("0.153"),
        qbi_rate=Decimal("0.20"),
    )
)
