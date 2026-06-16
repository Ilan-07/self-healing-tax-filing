"""End-to-end engine demo on synthetic data (no document upload needed).

Run:  python -m app.synthetic.demo
"""

from __future__ import annotations

from app.agents.tax_processing.tax_calculator import TaxCalculator
from app.agents.verification.agent import VerificationAgent
from app.synthetic import synthetic_return, synthetic_transcript


def main() -> None:
    data = synthetic_return(qualifying_children=1)
    transcript = synthetic_transcript(data)

    calculator = TaxCalculator()
    calculation = calculator.calculate(data)
    verification, _ = VerificationAgent(calculator, threshold=0.95).run(
        data, calculation, transcript=transcript
    )

    print(f"Taxpayer: {data.employee_name}  SSN {data.masked_ssn}")
    print(f"Filing status: {data.filing_status}  Tax year: {data.tax_year}")
    print("-" * 60)
    for line in calculation.trace:
        print(f"  {line}")
    print("-" * 60)
    print(f"AGI:              {calculation.adjusted_gross_income}")
    print(f"Taxable income:   {calculation.taxable_income}")
    print(f"Child tax credit: {calculation.child_tax_credit}")
    print(f"Federal tax:      {calculation.federal_tax}")
    print(f"Refund:           {calculation.refund}")
    print(f"Balance due:      {calculation.tax_due}")
    print("-" * 60)
    print(
        f"VALID={verification.valid}  confidence={verification.confidence_score} "
        f"correctness={verification.correctness_ok} "
        f"completeness={verification.completeness_ok}"
    )
    if verification.errors:
        print("Issues:")
        for err in verification.errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
