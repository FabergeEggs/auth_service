from pydantic import BaseModel, EmailStr, Field
from typing import Any


class RegisterRequestDTO(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterResponseDTO(BaseModel):
    user_id: str
    message: str = "User registered successfully"


class LoginRequestDTO(BaseModel):
    email: EmailStr
    password: str


class TokenResponseDTO(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int | None = None
    token_type: str = "bearer"
    scope: str | None = None


class RefreshTokenDTO(BaseModel):
    refresh_token: str


class LogoutRequestDTO(BaseModel):
    refresh_token: str


class MeResponseDTO(BaseModel):
    sub: str
    email: str | None = None
    preferred_username: str | None = None
    realm_roles: list[str] = Field(default_factory=list)
    client_roles: dict[str, list[str]] = Field(default_factory=dict)
    raw_claims: dict[str, Any] = Field(default_factory=dict)
