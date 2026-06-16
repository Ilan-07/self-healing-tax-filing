"""Federal tax parameters for tax year 2025.

Sources:
  * Rev. Proc. 2024-40 (2025 inflation adjustments): brackets, standard
    deduction, additional standard deduction, capital-gain breakpoints, EITC,
    AMT exemptions.
  * One Big Beautiful Bill Act (OBBBA, 2025): increased standard deduction,
    Child Tax Credit raised to $2,200, new senior deduction ($6,000, 2025-2028).
  * SSA 2025 OASDI wage base = $176,100.
  * IRC sec. 1411 (NIIT) / sec. 3101(b)(2) (Additional Medicare Tax) thresholds.

``verified=True``: brackets, standard/senior deductions, capital-gain
breakpoints, CTC, EITC (max credits + phase-out begin/end), and AMT exemptions
reconciled against Rev. Proc. 2024-40 / Tax Foundation 2025 summaries; structural
invariants are enforced by ``app.tax_rules.validation``.
"""

from decimal import Decimal

from app.schemas import FilingStatus
from app.tax_rules.params import (
    AmtParams,
    CreditParams,
    EducationCreditParams,
    EitcParams,
    EitcTier,
    PreferentialRates,
    SaversCreditParams,
    TaxYearParams,
    register,
)


STANDARD_DEDUCTIONS = {
    FilingStatus.SINGLE: Decimal("15750"),
    FilingStatus.MARRIED_JOINTLY: Decimal("31500"),
    FilingStatus.MARRIED_SEPARATELY: Decimal("15750"),
    FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("23625"),
}

# Each tuple is the upper bound for that band and its marginal rate.
BRACKETS = {
    FilingStatus.SINGLE: [
        (Decimal("11925"), Decimal("0.10")),
        (Decimal("48475"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250525"), Decimal("0.32")),
        (Decimal("626350"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_JOINTLY: [
        (Decimal("23850"), Decimal("0.10")),
        (Decimal("96950"), Decimal("0.12")),
        (Decimal("206700"), Decimal("0.22")),
        (Decimal("394600"), Decimal("0.24")),
        (Decimal("501050"), Decimal("0.32")),
        (Decimal("751600"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_SEPARATELY: [
        (Decimal("11925"), Decimal("0.10")),
        (Decimal("48475"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250525"), Decimal("0.32")),
        (Decimal("375800"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (Decimal("17000"), Decimal("0.10")),
        (Decimal("64850"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250500"), Decimal("0.32")),
        (Decimal("626350"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
}

PARAMS = register(
    TaxYearParams(
        year=2025,
        source="Rev. Proc. 2024-40; OBBBA 2025; SSA 2025",
        verified=True,
        standard_deductions=STANDARD_DEDUCTIONS,
        additional_std_married=Decimal("1600"),
        additional_std_unmarried=Decimal("2000"),
        brackets=BRACKETS,
        preferential=PreferentialRates(
            zero_rate_max={
                FilingStatus.SINGLE: Decimal("48350"),
                FilingStatus.MARRIED_JOINTLY: Decimal("96700"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("48350"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("64750"),
            },
            fifteen_rate_max={
                FilingStatus.SINGLE: Decimal("533400"),
                FilingStatus.MARRIED_JOINTLY: Decimal("600050"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("300000"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("566700"),
            },
        ),
        credits=CreditParams(
            ctc_per_child=Decimal("2200"),
            ctc_refundable_cap=Decimal("1700"),
            odc_per_dependent=Decimal("500"),
            phaseout_start={
                FilingStatus.SINGLE: Decimal("200000"),
                FilingStatus.MARRIED_JOINTLY: Decimal("400000"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("200000"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("200000"),
            },
            phaseout_per_1000=Decimal("50"),
        ),
        ss_wage_base=Decimal("176100"),
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
        eitc=EitcParams(
            investment_income_limit=Decimal("11950"),
            tiers={
                0: EitcTier(
                    credit_rate=Decimal("0.0765"),
                    earned_income_amount=Decimal("8490"),
                    max_credit=Decimal("649"),
                    phaseout_begin_other=Decimal("10620"),
                    phaseout_begin_mfj=Decimal("17730"),
                    phaseout_rate=Decimal("0.0765"),
                ),
                1: EitcTier(
                    credit_rate=Decimal("0.34"),
                    earned_income_amount=Decimal("12730"),
                    max_credit=Decimal("4328"),
                    phaseout_begin_other=Decimal("23350"),
                    phaseout_begin_mfj=Decimal("30470"),
                    phaseout_rate=Decimal("0.1598"),
                ),
                2: EitcTier(
                    credit_rate=Decimal("0.40"),
                    earned_income_amount=Decimal("17880"),
                    max_credit=Decimal("7152"),
                    phaseout_begin_other=Decimal("23350"),
                    phaseout_begin_mfj=Decimal("30470"),
                    phaseout_rate=Decimal("0.2106"),
                ),
                3: EitcTier(
                    credit_rate=Decimal("0.45"),
                    earned_income_amount=Decimal("17880"),
                    max_credit=Decimal("8046"),
                    phaseout_begin_other=Decimal("23350"),
                    phaseout_begin_mfj=Decimal("30470"),
                    phaseout_rate=Decimal("0.2106"),
                ),
            },
        ),
        amt=AmtParams(
            exemption={
                FilingStatus.SINGLE: Decimal("88100"),
                FilingStatus.MARRIED_JOINTLY: Decimal("137000"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("68500"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("88100"),
            },
            phaseout_start={
                FilingStatus.SINGLE: Decimal("626350"),
                FilingStatus.MARRIED_JOINTLY: Decimal("1252700"),
                FilingStatus.MARRIED_SEPARATELY: Decimal("626350"),
                FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("626350"),
            },
            rate_28_threshold=Decimal("239100"),
        ),
        education=EducationCreditParams(
            aotc_max_per_student=Decimal("2500"),
            aotc_refundable_rate=Decimal("0.40"),
            llc_rate=Decimal("0.20"),
            llc_expense_cap=Decimal("10000"),
            phaseout={
                FilingStatus.SINGLE: (Decimal("80000"), Decimal("90000")),
                FilingStatus.HEAD_OF_HOUSEHOLD: (Decimal("80000"), Decimal("90000")),
                FilingStatus.MARRIED_JOINTLY: (Decimal("160000"), Decimal("180000")),
            },
        ),
        savers=SaversCreditParams(
            contribution_cap=Decimal("2000"),
            tiers={
                FilingStatus.SINGLE: [
                    (Decimal("23750"), Decimal("0.50")),
                    (Decimal("25500"), Decimal("0.20")),
                    (Decimal("39500"), Decimal("0.10")),
                ],
                FilingStatus.MARRIED_SEPARATELY: [
                    (Decimal("23750"), Decimal("0.50")),
                    (Decimal("25500"), Decimal("0.20")),
                    (Decimal("39500"), Decimal("0.10")),
                ],
                FilingStatus.HEAD_OF_HOUSEHOLD: [
                    (Decimal("35625"), Decimal("0.50")),
                    (Decimal("38250"), Decimal("0.20")),
                    (Decimal("59250"), Decimal("0.10")),
                ],
                FilingStatus.MARRIED_JOINTLY: [
                    (Decimal("47500"), Decimal("0.50")),
                    (Decimal("51000"), Decimal("0.20")),
                    (Decimal("79000"), Decimal("0.10")),
                ],
            },
        ),
        senior_deduction=Decimal("6000"),
        senior_deduction_phaseout_start={
            FilingStatus.SINGLE: Decimal("75000"),
            FilingStatus.MARRIED_JOINTLY: Decimal("150000"),
            FilingStatus.MARRIED_SEPARATELY: Decimal("75000"),
            FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("75000"),
        },
        senior_deduction_phaseout_rate=Decimal("0.06"),
    )
)
