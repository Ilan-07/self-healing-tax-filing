"""API-key authentication.

When ``settings.api_key`` is set, requests must send a matching ``X-API-Key``
header. When it is empty (local development default) auth is disabled.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if not expected:
        return  # auth disabled in local/dev mode
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
