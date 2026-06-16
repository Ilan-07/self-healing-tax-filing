"""Typed extractors for information returns other than the W-2.

A document is segmented into form *instances* (by form-type markers), each
instance is classified and dispatched to a form-specific parser, and the parsed
amounts are **summed** across instances into taxpayer-level fields. This gives
1099s / K-1 / 1098 the same structured, source-grounded treatment as the W-2,
including correct handling of multiple forms of the same type.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.services.extraction.w2_parser import _find_amount_after


CONFIDENCE = 0.88

# Form id -> header marker. Ordered so specific patterns win over generic ones.
FORM_MARKERS: dict[str, str] = {
    "1099-INT": r"1099-?\s?int",
    "1099-DIV": r"1099-?\s?div",
    "1099-NEC": r"1099-?\s?nec",
    "1099-MISC": r"1099-?\s?misc",
    "1099-R": r"1099-?\s?r(?![a-z])",
    "1099-B": r"1099-?\s?b(?![a-z])",
    "1099-G": r"1099-?\s?g(?![a-z])",
    "SSA-1099": r"ssa-?\s?1099",
    "K-1": r"schedule\s*k-?1|\bk-?1\b",
    "1098-T": r"1098-?\s?t",
    "1098": r"1098(?!-?\s?t)",
    "W-2": r"\bw-?2\b",
}


def _amt(seg: str, label: str) -> Decimal | None:
    return _find_amount_after(seg, label)


def _parse_1099_int(seg: str) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    if (v := _amt(seg, r"interest\s+income")) is not None:
        out["taxable_interest"] = v
    if (v := _amt(seg, r"tax-?exempt\s+interest")) is not None:
        out["tax_exempt_interest"] = v
    return out


def _parse_1099_div(seg: str) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    if (v := _amt(seg, r"(?:total\s+)?ordinary\s+dividends")) is not None:
        out["ordinary_dividends"] = v
    if (v := _amt(seg, r"qualified\s+dividends")) is not None:
        out["qualified_dividends"] = v
    if (v := _amt(seg, r"(?:total\s+)?capital\s+gain\s+distr")) is not None:
        out["long_term_capital_gain"] = v
    return out


def _parse_1099_r(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"taxable\s+amount")) is not None:
        return {"taxable_pension_ira": v}
    return {}


def _parse_1099_nec(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"nonemployee\s+compensation")) is not None:
        return {"self_employment_income": v}
    return {}


def _parse_1099_misc(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"other\s+income")) is not None:
        return {"other_income": v}
    return {}


def _parse_1099_g(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"unemployment\s+compensation")) is not None:
        return {"other_income": v}
    return {}


def _parse_ssa(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"net\s+benefits")) is not None:
        return {"social_security_benefits": v}
    if (v := _amt(seg, r"benefits\s+paid")) is not None:
        return {"social_security_benefits": v}
    return {}


def _parse_1098(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"mortgage\s+interest")) is not None:
        return {"mortgage_interest": v}
    return {}


def _parse_1098_t(seg: str) -> dict[str, Decimal]:
    if (v := _amt(seg, r"payments\s+received|qualified\s+tuition")) is not None:
        return {"qualified_tuition": v}
    return {}


def _parse_1099_b(seg: str) -> dict[str, Decimal]:
    """Parse the short/long-term summary totals (proceeds - cost basis)."""
    out: dict[str, Decimal] = {}
    for term, field in (
        ("short", "short_term_capital_gain"),
        ("long", "long_term_capital_gain"),
    ):
        marker = re.search(rf"{term}[-\s]term", seg, re.IGNORECASE)
        if not marker:
            continue
        sub = seg[marker.start() : marker.start() + 220]
        proceeds = _amt(sub, r"proceeds")
        basis = _amt(sub, r"cost\s*(?:or\s*other\s*)?basis|\bbasis")
        if proceeds is not None and basis is not None:
            out[field] = proceeds - basis
        elif (gain := _amt(sub, r"gain\s*or\s*\(?loss\)?|realized\s+gain")) is not None:
            out[field] = gain
    return out


def _parse_k1(seg: str) -> dict[str, Decimal]:
    """Route each Schedule K-1 box to the matching taxpayer field."""
    out: dict[str, Decimal] = {}
    mapping = [
        (r"ordinary\s+business\s+income", "partnership_income"),
        (r"net\s+rental\s+real\s+estate", "partnership_income"),
        (r"interest\s+income", "taxable_interest"),
        (r"ordinary\s+dividends", "ordinary_dividends"),
        (r"qualified\s+dividends", "qualified_dividends"),
        (r"net\s+short-?term\s+capital\s+gain", "short_term_capital_gain"),
        (r"net\s+long-?term\s+capital\s+gain", "long_term_capital_gain"),
    ]
    for pattern, field in mapping:
        if (v := _amt(seg, pattern)) is not None and v > 0:
            out[field] = out.get(field, Decimal("0")) + v
    return out


FORM_PARSERS = {
    "1099-INT": _parse_1099_int,
    "1099-DIV": _parse_1099_div,
    "1099-R": _parse_1099_r,
    "1099-NEC": _parse_1099_nec,
    "1099-MISC": _parse_1099_misc,
    "1099-G": _parse_1099_g,
    "SSA-1099": _parse_ssa,
    "1099-B": _parse_1099_b,
    "K-1": _parse_k1,
    "1098": _parse_1098,
    "1098-T": _parse_1098_t,
    # "W-2" intentionally omitted: handled by the dedicated W-2 extractor.
}


def classify_form(text: str) -> str:
    for fid, pattern in FORM_MARKERS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return fid
    return "unknown"


def _segments(text: str) -> list[tuple[str, str]]:
    """Slice the document into (form_id, segment_text) by form-type markers."""
    hits: list[tuple[int, str]] = []
    for fid, pattern in FORM_MARKERS.items():
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append((m.start(), fid))
    if not hits:
        return []
    hits.sort()
    segments: list[tuple[str, str]] = []
    for i, (start, fid) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        segments.append((fid, text[start:end]))
    return segments


def extract_information_returns(text: str) -> dict[str, tuple[Decimal, float]]:
    """Sum per-form parsed amounts into taxpayer fields, with confidences."""
    totals: dict[str, Decimal] = {}
    if not text or not text.strip():
        return {}
    for fid, seg in _segments(text):
        parser = FORM_PARSERS.get(fid)
        if parser is None:
            continue
        for field, amount in parser(seg).items():
            if amount and amount > 0:
                totals[field] = totals.get(field, Decimal("0")) + amount
    return {field: (value, CONFIDENCE) for field, value in totals.items()}
