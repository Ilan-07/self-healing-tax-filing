"""Label/box-number anchored W-2 parser.

Robust to OCR noise and layout drift: it locates each box by its printed label
or box number and grabs the nearest currency amount, rather than relying on
fixed pixel crop regions. Multiple W-2s in one document are segmented by
employer EIN.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas import W2
from app.services.extraction.base import ParsedW2


# Ordered label alternatives per box. Box-number anchors are last (lower trust).
BOX_LABELS: dict[str, list[str]] = {
    "box1_wages": [r"wages,?\s*tips[^\n]*compensation", r"\bbox\s*1\b"],
    "box2_federal_withheld": [r"federal\s+income\s+tax\s+withheld", r"\bbox\s*2\b"],
    "box3_ss_wages": [r"social\s+security\s+wages", r"\bbox\s*3\b"],
    "box4_ss_withheld": [r"social\s+security\s+tax\s+withheld", r"\bbox\s*4\b"],
    "box5_medicare_wages": [r"medicare\s+wages(?:\s+and\s+tips)?", r"\bbox\s*5\b"],
    "box6_medicare_withheld": [r"medicare\s+tax\s+withheld", r"\bbox\s*6\b"],
    "box17_state_withheld": [r"state\s+income\s+tax", r"\bbox\s*17\b"],
}

# A currency amount, tolerant of OCR spacing and thousands separators.
# Prefer a decimal-terminated number (allowing stray internal spaces/commas);
# fall back to a plain integer.
# 1-2 decimals: OCR sometimes drops a trailing zero (e.g. "17995.3").
AMOUNT_DECIMAL = re.compile(r"(\d[\d,\s]{0,15}[.,]\s?\d{1,2})")
AMOUNT_INT = re.compile(r"(\d[\d,]{0,15})")
EIN = re.compile(r"\b(\d{2}-\d{7})\b")
SSN = re.compile(r"\b(\d{3}-\d{2}-\d{4})\b")
YEAR = re.compile(r"\b(20\d{2})\b")
# Box 15 "Employer's state" -- the 2-letter code following the box 15 label.
STATE_CODE = re.compile(
    r"(?:\bbox\s*15\b|employer'?s?\s+state)[^A-Za-z]{0,8}([A-Z]{2})\b"
)

LABEL_CONFIDENCE = 0.9
BOXNUM_CONFIDENCE = 0.8
# How far after a label we will look for the amount (chars, incl. newlines).
LOOKAHEAD = 60


def _to_decimal(raw: str) -> Decimal | None:
    s = re.sub(r"\s", "", raw)
    if "." in s:
        s = s.replace(",", "")  # dot is the decimal point; commas are grouping
    elif re.search(r",\d{2}$", s):
        # Comma used as the decimal separator (e.g. "1234,56").
        head, _, tail = s.rpartition(",")
        s = head.replace(",", "") + "." + tail
    else:
        s = s.replace(",", "")
    try:
        value = Decimal(s)
    except (InvalidOperation, ValueError):
        return None
    return value if value >= 0 else None


def _find_amount_after(text: str, label_pattern: str) -> Decimal | None:
    for match in re.finditer(label_pattern, text, flags=re.IGNORECASE):
        window = text[match.end() : match.end() + LOOKAHEAD]
        amount_match = AMOUNT_DECIMAL.search(window) or AMOUNT_INT.search(window)
        if amount_match:
            value = _to_decimal(amount_match.group(1))
            if value is not None:
                return value
    return None


class LabelAnchoredW2Parser:
    name = "label_anchored_w2"

    def parse(self, *, ocr_text: str, image: Any | None = None) -> list[ParsedW2]:
        if not ocr_text or not ocr_text.strip():
            return []
        return [self._parse_segment(seg) for seg in self._segments(ocr_text)]

    def _segments(self, text: str) -> list[str]:
        """Split into one segment per employer EIN (multi-W-2 documents)."""
        positions = [m.start() for m in EIN.finditer(text)]
        if len(positions) <= 1:
            return [text]
        bounds = positions + [len(text)]
        return [text[bounds[i] : bounds[i + 1]] for i in range(len(positions))]

    def _parse_segment(self, text: str) -> ParsedW2:
        values: dict[str, Any] = {}
        confidences: dict[str, float] = {}
        for box, patterns in BOX_LABELS.items():
            for index, pattern in enumerate(patterns):
                amount = _find_amount_after(text, pattern)
                if amount is not None:
                    values[box] = amount
                    confidences[box] = (
                        LABEL_CONFIDENCE if index == 0 else BOXNUM_CONFIDENCE
                    )
                    break

        ein_match = EIN.search(text)
        ssn_match = SSN.search(text)
        year_match = YEAR.findall(text)
        state_match = STATE_CODE.search(text)
        if state_match:
            values["box15_state"] = state_match.group(1)

        # Positional fallback for real W-2 forms: OCR garbles the box labels and
        # the form layout separates labels from values, so when the labels can't
        # be matched, take the two amounts printed right after the EIN as box 1
        # (wages) and box 2 (federal withholding) -- the high-confidence pair.
        # SS/Medicare boxes are left to label matching to avoid mis-pairing on
        # multi-employer forms (the verification invariants would flag bad data).
        if "box1_wages" not in values and ein_match:
            after = text[ein_match.end() :]
            amounts: list[Decimal] = []
            for m in AMOUNT_DECIMAL.finditer(after):
                value = _to_decimal(m.group(1))
                if value is not None and value > 0:
                    amounts.append(value)
                if len(amounts) >= 2:
                    break
            if amounts:
                values["box1_wages"] = amounts[0]
                confidences["box1_wages"] = 0.6
                if len(amounts) >= 2:
                    values["box2_federal_withheld"] = amounts[1]
                    confidences["box2_federal_withheld"] = 0.6

        w2 = W2(employer_ein=ein_match.group(1) if ein_match else "", **values)
        return ParsedW2(
            w2=w2,
            ssn=ssn_match.group(1) if ssn_match else "",
            tax_year=int(year_match[-1]) if year_match else None,
            confidences=confidences,
        )
