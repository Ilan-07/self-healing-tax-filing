"""Pluggable W-2 extraction.

The default ``LabelAnchoredW2Parser`` reads box values by anchoring on box
labels / numbers in the OCR text (tolerant of noise and layout changes) instead
of fixed pixel crop regions, and segments multiple W-2s by employer EIN.

``CloudW2Extractor`` is the production swap-in: a thin adapter over a cloud W-2
form model (Azure Document Intelligence prebuilt-W2, AWS Textract Queries, or
Google Document AI). Both satisfy the same ``W2Extractor`` protocol, so the
reading agent does not change when you upgrade extraction quality.
"""

from app.services.extraction.base import ParsedW2, W2Extractor
from app.services.extraction.cloud import CloudW2Extractor
from app.services.extraction.w2_parser import LabelAnchoredW2Parser

__all__ = [
    "ParsedW2",
    "W2Extractor",
    "CloudW2Extractor",
    "LabelAnchoredW2Parser",
    "get_w2_extractor",
]


def get_w2_extractor(
    name: str = "label",
    *,
    azure_endpoint: str = "",
    azure_key: str = "",
) -> W2Extractor:
    """Select a W-2 extractor; fall back to the offline parser on any problem.

    ``name="azure"`` uses Azure Document Intelligence's prebuilt W-2 model when
    credentials are present and the SDK is installed; otherwise the robust
    offline ``LabelAnchoredW2Parser`` is used so the app always runs.
    """
    if name == "azure" and azure_endpoint and azure_key:
        try:
            from app.services.extraction.azure_client import build_azure_w2_client

            return CloudW2Extractor(build_azure_w2_client(azure_endpoint, azure_key))
        except Exception:  # missing SDK / bad config -> graceful fallback
            return LabelAnchoredW2Parser()
    return LabelAnchoredW2Parser()
