import httpx
from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    ollama = False
    try:
        ollama = (
            httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2).status_code
            == 200
        )
    except httpx.HTTPError:
        pass
    return {"status": "ok", "ollama": ollama}
