from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.schemas import AuditEntry, TaxpayerData


class TaxProcessingAgent:
    name = "Tax Processing Agent"

    def __init__(self, calculator: TaxCalculator):
        self.calculator = calculator

    def run(self, data: TaxpayerData):
        calculation = self.calculator.calculate(data)
        log = AuditEntry(
            agent=self.name,
            action="calculate_tax",
            reason=(
                f"Apply authoritative {data.tax_year} deterministic tax rules"
            ),
            details={
                "taxable_income": str(calculation.taxable_income),
                "total_tax": str(calculation.total_tax),
            },
        )
        return calculation, log
