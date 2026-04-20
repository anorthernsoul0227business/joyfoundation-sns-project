
from pydantic import BaseModel, EmailStr, Field, SecretStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = None
    ui_mode: str = "simple"
    help_mode_enabled: bool = True
    default_org_id: str | None = None


class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
