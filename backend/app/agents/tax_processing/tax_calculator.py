from decimal import Decimal, ROUND_HALF_UP

from app.schemas import TaxCalculation, TaxpayerData
from app.tax_rules import federal_2018, federal_2025


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class TaxCalculator:
    def calculate(self, data: TaxpayerData) -> TaxCalculation:
        rule_sets = {
            2018: federal_2018,
            2025: federal_2025,
        }
        rules = rule_sets.get(data.tax_year)
        if not rules:
            raise ValueError(
                f"No federal tax rule set is installed for {data.tax_year}"
            )

        gross_income = money(data.wages + data.other_income)
        standard = rules.STANDARD_DEDUCTIONS[data.filing_status]
        deductions = max(standard, data.itemized_deductions)
        taxable = money(max(Decimal("0"), gross_income - deductions))
        federal, trace = self._progressive_tax(
            taxable, rules.BRACKETS[data.filing_status]
        )
        state_tax = money(taxable * data.state_tax_rate)
        total_tax = money(federal + state_tax)
        withholding = money(
            data.federal_tax_withheld + data.state_tax_withheld
        )
        balance = money(withholding - total_tax)

        return TaxCalculation(
            gross_income=gross_income,
            standard_deduction=money(standard),
            deductions=money(deductions),
            taxable_income=taxable,
            federal_tax=federal,
            state_tax=state_tax,
            total_tax=total_tax,
            total_withholding=withholding,
            refund=max(Decimal("0"), balance),
            tax_due=max(Decimal("0"), -balance),
            trace=[
                f"Gross income: {gross_income}",
                f"Deduction used: {deductions}",
                f"Taxable income: {taxable}",
                *trace,
                f"State tax at {data.state_tax_rate}: {state_tax}",
            ],
        )

    def _progressive_tax(
        self,
        taxable: Decimal,
        brackets: list[tuple[Decimal | None, Decimal]],
    ) -> tuple[Decimal, list[str]]:
        tax = Decimal("0")
        lower = Decimal("0")
        trace: list[str] = []
        for upper, rate in brackets:
            if taxable <= lower:
                break
            band_top = taxable if upper is None else min(taxable, upper)
            amount = max(Decimal("0"), band_top - lower)
            band_tax = amount * rate
            tax += band_tax
            trace.append(
                f"{money(amount)} taxed at {rate * 100}% = {money(band_tax)}"
            )
            if upper is None or taxable <= upper:
                break
            lower = upper
        return money(tax), trace
