from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class RegisterRequestDTO(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        validation_alias=AliasChoices("username", "login"),
    )
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterResponseDTO(BaseModel):
    user_id: str
    message: str = "User registered successfully"


class LoginRequestDTO(BaseModel):
    email: EmailStr = Field(
        ...,
        validation_alias=AliasChoices("email", "login"),
    )
    password: str


class TokenResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int | None = None
    token_type: str = "bearer"
    scope: str | None = None


class RefreshTokenDTO(BaseModel):
    refresh_token: str = Field(
        ...,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
    )


class LogoutRequestDTO(BaseModel):
    refresh_token: str = Field(
        ...,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
    )


class MeResponseDTO(BaseModel):
    sub: str
    email: str | None = None
    preferred_username: str | None = None
    realm_roles: list[str] = Field(default_factory=list)
    client_roles: dict[str, list[str]] = Field(default_factory=dict)
    raw_claims: dict[str, Any] = Field(default_factory=dict)
