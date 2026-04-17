from fastapi import FastAPI

from app.config import get_settings
from app.schemas.health import HealthResponse

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")
