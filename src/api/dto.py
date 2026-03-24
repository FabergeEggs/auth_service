from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class RegisterRequestDTO(BaseModel):
    username: str = Field(  # Сделаем username обязательным
        ...,
        min_length=3,
        max_length=50,
        validation_alias=AliasChoices("username", "login"),
    )
    email: EmailStr
    password: str = Field(..., min_length=6)
    # Опциональные поля
    first_name: Optional[str] = Field(None, max_length=50, description="Имя")
    last_name: Optional[str] = Field(None, max_length=50, description="Фамилия")
    about: Optional[str] = Field(None, max_length=500, description="О себе")
    phone: Optional[str] = Field(None, max_length=20, description="Телефон")


class RegisterResponseDTO(BaseModel):
    user_id: str
    message: str = "User registered successfully"


class LoginRequestDTO(BaseModel):
    # Логин может быть email или username
    login: str = Field(
        ...,
        min_length=3,
        validation_alias=AliasChoices("login", "email"),
        description="Email or username"
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
    name: str | None = None  # Полное имя
    given_name: str | None = None  # Имя
    family_name: str | None = None  # Фамилия
    phone: str | None = None  # Телефон
    about: str | None = None  # О себе
    realm_roles: list[str] = Field(default_factory=list)
    client_roles: dict[str, list[str]] = Field(default_factory=dict)
    raw_claims: dict[str, Any] = Field(default_factory=dict)