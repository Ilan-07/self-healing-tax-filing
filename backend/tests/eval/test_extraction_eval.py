"""Extraction-quality evaluation for the W-2 parser.

Measures field-level accuracy and hallucination rate against synthetic ground
truth -- the kind of guardrail you want around the riskiest (extraction) stage.
The core eval is plain pytest so it always runs; an optional deepeval wrapper
runs the same metric through deepeval when that package is installed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.extraction import LabelAnchoredW2Parser


def _w2_text(wages: int, fed: int, ssn: str, ein: str) -> str:
    ss_tax = round(wages * 0.062, 2)
    med_tax = round(wages * 0.0145, 2)
    return f"""
Form W-2 Wage and Tax Statement 2025
Employer identification number (EIN) {ein}
Employee SSN {ssn}
1 Wages, tips, other compensation {wages}.00
2 Federal income tax withheld {fed}.00
3 Social security wages {wages}.00
4 Social security tax withheld {ss_tax}
5 Medicare wages and tips {wages}.00
6 Medicare tax withheld {med_tax}
"""


CASES = [
    (85000, 11000, "123-45-6789", "12-3456789"),
    (52000, 4200, "987-65-4321", "98-7654321"),
    (143250, 26010, "111-22-3333", "45-6789012"),
    (9000, 300, "222-33-4444", "23-4567890"),
]


def _score() -> tuple[float, float]:
    """Return (field_accuracy, hallucination_rate) over the synthetic set."""
    parser = LabelAnchoredW2Parser()
    correct = total = produced = hallucinated = 0
    for wages, fed, ssn, ein in CASES:
        parsed = parser.parse(ocr_text=_w2_text(wages, fed, ssn, ein))
        assert len(parsed) == 1
        w2 = parsed[0].w2
        expected = {
            "box1_wages": Decimal(f"{wages}.00"),
            "box2_federal_withheld": Decimal(f"{fed}.00"),
            "box3_ss_wages": Decimal(f"{wages}.00"),
        }
        for field, want in expected.items():
            total += 1
            if getattr(w2, field) == want:
                correct += 1
        # Hallucination: a confident box value with no real underlying amount.
        for box in parsed[0].confidences:
            produced += 1
            if getattr(w2, box) <= 0:
                hallucinated += 1
    accuracy = correct / total
    hallucination_rate = (hallucinated / produced) if produced else 0.0
    return accuracy, hallucination_rate


def test_extraction_accuracy_meets_threshold():
    accuracy, hallucination_rate = _score()
    assert accuracy >= 0.95, f"extraction accuracy {accuracy:.2%} below 95%"
    assert hallucination_rate == 0.0, f"hallucination rate {hallucination_rate:.2%}"


def test_extraction_eval_via_deepeval():
    """Same metric expressed through deepeval, when it is installed."""
    deepeval = pytest.importorskip("deepeval")
    from deepeval.metrics import BaseMetric
    from deepeval.test_case import LLMTestCase

    accuracy, _ = _score()

    class ExtractionAccuracy(BaseMetric):
        threshold = 0.95

        def measure(self, test_case: LLMTestCase) -> float:
            self.score = accuracy
            self.success = accuracy >= self.threshold
            return self.score

        async def a_measure(self, test_case: LLMTestCase) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            return bool(self.success)

        @property
        def __name__(self) -> str:
            return "W-2 Extraction Accuracy"

    case = LLMTestCase(input="synthetic W-2 set", actual_output="parsed")
    deepeval.assert_test(case, [ExtractionAccuracy()])
