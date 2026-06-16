"""Synthetic taxpayer data for demos, tests, and eval ground truth.

Everything here is fabricated -- no real PII -- so the full pipeline can run
end to end without uploading real documents.
"""

from app.synthetic.generator import synthetic_return, synthetic_transcript

__all__ = ["synthetic_return", "synthetic_transcript"]
