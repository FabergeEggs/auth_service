from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError

from src.api.dto import (
    RegisterRequestDTO,
    RegisterResponseDTO,
    LoginRequestDTO,
    TokenResponseDTO,
    RefreshTokenDTO,
    LogoutRequestDTO,
    MeResponseDTO,
)
from src.api.dependencies import get_current_claims
from src.core.settings import settings
from src.services.keycloak_client import KeycloakClient, KeycloakConflictError

app = FastAPI(title="Auth Service")

kc = KeycloakClient(
    token_url=settings.token_url,
    logout_url=settings.logout_url,
    admin_users_url=settings.admin_users_url,
    client_id=settings.keycloak_client_id,
    client_secret=settings.keycloak_client_secret,
)


@app.post("/auth/register", response_model=RegisterResponseDTO)
async def register(payload: RegisterRequestDTO) -> RegisterResponseDTO:
    try:
        user_id = await kc.register(
            username=payload.username,
            email=payload.email,
            password=payload.password,
        )
        return RegisterResponseDTO(user_id=user_id)
    except KeycloakConflictError:
        raise HTTPException(status_code=409, detail="User already exists")
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Registration failed")


@app.post("/auth/login", response_model=TokenResponseDTO)
async def login(payload: LoginRequestDTO) -> TokenResponseDTO:
    try:
        data = await kc.password_login(
            username=payload.email,
            password=payload.password,
        )
        return TokenResponseDTO(**data)
    except HTTPStatusError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/refresh", response_model=TokenResponseDTO)
async def refresh(payload: RefreshTokenDTO) -> TokenResponseDTO:
    try:
        data = await kc.refresh(payload.refresh_token)
        return TokenResponseDTO(**data)
    except HTTPStatusError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.post("/auth/logout")
async def logout(payload: LogoutRequestDTO) -> JSONResponse:
    try:
        await kc.logout(payload.refresh_token)
        return JSONResponse({"status": "ok"})
    except HTTPStatusError:
        raise HTTPException(status_code=400, detail="Logout failed")


@app.get("/auth/me", response_model=MeResponseDTO)
async def me(claims: dict = Depends(get_current_claims)) -> MeResponseDTO:
    return MeResponseDTO(
        sub=claims.get("sub", ""),
        email=claims.get("email"),
        preferred_username=claims.get("preferred_username"),
        realm_roles=claims.get("realm_access", {}).get("roles", []),
        client_roles={
            client: data.get("roles", [])
            for client, data in claims.get("resource_access", {}).items()
        },
        raw_claims=claims,
    )


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
