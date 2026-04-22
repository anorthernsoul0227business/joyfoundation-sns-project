from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.calendar import router as calendar_router
from app.api.media import router as media_router
from app.api.notifications import router as notifications_router
from app.api.notifications_ws import router as notifications_ws_router
from app.api.posts import router as posts_router
from app.api.sns_accounts import router as sns_accounts_router
from app.config import get_settings
from app.schemas.health import HealthResponse

settings = get_settings()

app = FastAPI(title=settings.app_name)

allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(posts_router, prefix="/api/posts", tags=["posts"])
app.include_router(calendar_router, prefix="/api/calendar", tags=["calendar"])
app.include_router(sns_accounts_router, prefix="/api/sns-accounts", tags=["sns-accounts"])
app.include_router(media_router, prefix="/api/media", tags=["media"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(notifications_ws_router, prefix="/ws", tags=["notifications-ws"])


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")
