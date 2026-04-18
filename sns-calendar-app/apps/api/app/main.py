from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.config import get_settings
from app.schemas.health import HealthResponse

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")
