from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.schemas import W2


# W-2 box attribute on the ``W2`` model -> the taxpayer-level field it feeds.
BOX_TO_TAXPAYER_FIELD = {
    "box1_wages": "wages",
    "box2_federal_withheld": "federal_tax_withheld",
    "box17_state_withheld": "state_tax_withheld",
}


@dataclass
class ParsedW2:
    """One extracted W-2 plus per-field confidences and identity hints."""

    w2: W2
    employee_name: str = ""
    ssn: str = ""
    tax_year: int | None = None
    # Confidence keyed by W2 box attribute (e.g. "box1_wages").
    confidences: dict[str, float] = field(default_factory=dict)


class W2Extractor(Protocol):
    name: str

    def parse(self, *, ocr_text: str, image: Any | None = None) -> list[ParsedW2]:
        ...
