"""Cloud W-2 form-model adapter (production swap-in).

Wraps a cloud document model that returns structured W-2 boxes -- e.g. Azure
Document Intelligence ``prebuilt-tax.us.w2``, AWS Textract ``AnalyzeDocument``
Queries, or Google Document AI's W-2 parser. Inject a ``client`` callable that
takes image bytes and returns a list of ``{box_attr: value}`` dicts; this class
maps that into the same ``ParsedW2`` shape the rest of the pipeline consumes.

Left as an adapter (not a hard dependency) so the project runs fully offline,
while the integration point is real and documented.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any, Callable

from app.schemas import W2
from app.schemas.tax import normalize_state
from app.services.extraction.base import ParsedW2

# Confidence we attribute to a cloud form model when it omits per-field scores.
DEFAULT_CLOUD_CONFIDENCE = 0.97

ClientFn = Callable[[bytes], list[dict[str, Any]]]


class CloudW2Extractor:
    name = "cloud_w2_model"

    _NUMERIC_BOXES = {
        "box1_wages",
        "box2_federal_withheld",
        "box3_ss_wages",
        "box4_ss_withheld",
        "box5_medicare_wages",
        "box6_medicare_withheld",
        "box17_state_withheld",
    }

    def __init__(self, client: ClientFn | None = None):
        self.client = client

    def parse(self, *, ocr_text: str, image: Any | None = None) -> list[ParsedW2]:
        if self.client is None:
            raise NotImplementedError(
                "CloudW2Extractor requires a `client` callable wrapping a cloud "
                "W-2 model (Azure/Textract/Document AI). Use "
                "LabelAnchoredW2Parser for offline runs."
            )
        if image is None:
            return []
        try:
            results = self.client(_to_png_bytes(image))
        except Exception as exc:
            raise NotImplementedError(
                f"Cloud W-2 extraction unavailable: {exc}"
            ) from exc
        return [self._to_parsed(form) for form in results]

    def _to_parsed(self, form: dict[str, Any]) -> ParsedW2:
        box_attrs: dict[str, Decimal] = {}
        for key in self._NUMERIC_BOXES:
            value = _decimal_value(form.get(key))
            if value is not None:
                box_attrs[key] = value
        return ParsedW2(
            w2=W2(
                employer_ein=str(form.get("employer_ein", "")),
                box15_state=normalize_state(form.get("box15_state")),
                **box_attrs,
            ),
            employee_name=str(form.get("employee_name", "")),
            ssn=str(form.get("ssn", "")),
            tax_year=form.get("tax_year"),
            confidences={
                k: float(form.get(f"{k}_confidence", DEFAULT_CLOUD_CONFIDENCE))
                for k in box_attrs
            },
        )


def _decimal_value(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_png_bytes(image: Any) -> bytes:
    buffer = io.BytesIO()
    rgb = image.convert("RGB")
    max_side = 1800
    scale = min(max_side / max(rgb.size), 1.0)
    if scale < 1:
        rgb = rgb.resize((int(rgb.width * scale), int(rgb.height * scale)))
    rgb.save(buffer, format="PNG")
    return buffer.getvalue()
