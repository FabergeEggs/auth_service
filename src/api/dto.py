from typing import Optional, Dict, List, Any
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class ForgotPasswordRequestDTO(BaseModel):
    email: EmailStr


class ResetPasswordRequestDTO(BaseModel):
    key: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class VerifyEmailRequestDTO(BaseModel):
    key: str = Field(..., min_length=1)


class RegisterRequestDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    about: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)


class RegisterResponseDTO(BaseModel):
    user_id: str
    message: str = "User registered successfully"


class LoginRequestDTO(BaseModel):
    login: str = Field(
        ..., min_length=3, validation_alias=AliasChoices("login", "email")
    )
    password: str = Field(..., min_length=1)


class TokenResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    access_token: str
    expires_in: int
    refresh_expires_in: int | None = None
    token_type: str = "bearer"
    scope: str | None = None
    user_id: str | None = None


class MeResponseDTO(BaseModel):
    sub: str
    email: str | None = None
    preferred_username: str | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    phone: str | None = None
    about: str | None = None
    realm_roles: List[str] = Field(default_factory=list)
    client_roles: Dict[str, List[str]] = Field(default_factory=dict)
    raw_claims: Dict[str, Any] = Field(default_factory=dict)
