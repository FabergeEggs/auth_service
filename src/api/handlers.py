import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.adapters.keycloak_adapter import KeycloakUnavailableError
from src.api.dto import LoginRequestDTO, MeResponseDTO, RegisterRequestDTO, RegisterResponseDTO
from src.service.auth_service import AuthService, UserAlreadyExistsError
from src.config import settings

logger = logging.getLogger("auth_service.api")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1")


async def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_token_verifier(request: Request):
    return request.app.state.token_verifier


async def get_current_claims(
    request: Request,   
    authorization: str = Header(default="")
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    verifier = await get_token_verifier(request)
    try:
        return await verifier.verify(token)
    except ValueError as e:
        raise HTTPException(401, str(e))


@router.post("/auth/register", response_model=RegisterResponseDTO)
@limiter.limit("3/minute")
async def register(payload: RegisterRequestDTO, request: Request):
    business = await get_auth_service(request)
    try:
        uid = await business.register(
            email=payload.email, password=payload.password,
            first_name=payload.first_name, last_name=payload.last_name,
            phone=payload.phone, about=payload.about
        )
        return RegisterResponseDTO(user_id=uid)
    except UserAlreadyExistsError:
        raise HTTPException(409, "User already exists")
    except HTTPStatusError as e:
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error_description", "Invalid password policy")
                raise HTTPException(400, f"Registration failed: {error_msg}")
            except Exception:
                logger.warning("Keycloak returned 400 but response is not JSON: %s", e.response.text)
                raise HTTPException(400, "Registration failed: invalid data")
        raise HTTPException(e.response.status_code, "Registration failed")
    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")
    except Exception:
        logger.exception("Unexpected register error")
        raise HTTPException(500, "Internal error")


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequestDTO):
    business = await get_auth_service(request)
    try:
        data = await business.login(login=payload.login, password=payload.password)
        logger.info("Login success", extra={"event": "login_success"})
        resp = JSONResponse({
            "access_token": data["access_token"],
            "expires_in": data["expires_in"],
            "refresh_expires_in": data.get("refresh_expires_in"),
            "token_type": data.get("token_type", "bearer"),
            "scope": data.get("scope")
        })
        max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
        is_production = (settings.environment == "production")
        if max_age > 0:
            resp.set_cookie(
                "refresh_token", data["refresh_token"],
                httponly=True, secure=is_production, samesite="lax",
                max_age=max_age, path="/api/v1/auth"
            )
        return resp
    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")
    except HTTPStatusError:
        logger.warning("Login failed")
        raise HTTPException(401, "Invalid credentials")


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request):
    business = await get_auth_service(request)
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        data = await business.refresh(token)
        resp = JSONResponse({
            "access_token": data["access_token"],
            "expires_in": data["expires_in"],
            "refresh_expires_in": data.get("refresh_expires_in"),
            "token_type": data.get("token_type", "bearer"),
            "scope": data.get("scope")
        })
        if "refresh_token" in data:
            max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
            is_production = (settings.environment == "production")
            resp.set_cookie(
                "refresh_token", data["refresh_token"],
                httponly=True, secure=is_production, samesite="lax",
                max_age=max_age, path="/api/v1/auth"
            )
        return resp
    except HTTPStatusError:
        resp = JSONResponse({"detail": "Invalid refresh token"}, status_code=401)
        is_production = (settings.environment == "production")
        resp.delete_cookie(
            "refresh_token", path="/api/v1/auth",
            httponly=True, secure=is_production, samesite="lax"
        )
        return resp
    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")

@router.post("/auth/logout")
@limiter.limit("5/minute")
async def logout(request: Request):
    business = await get_auth_service(request)
    token = request.cookies.get("refresh_token")
    resp = JSONResponse({"status": "ok"})
    if token:
        try:
            await business.logout(token)
        except HTTPStatusError:
            pass
        except KeycloakUnavailableError:
            raise HTTPException(503, "Authentication service temporarily unavailable")
        finally:
            is_production = (settings.environment == "production")
            resp.delete_cookie(
                "refresh_token", path="/api/v1/auth",
                httponly=True, secure=is_production, samesite="lax"
            )
    return resp


@router.post("/auth/logout-all")
@limiter.limit("5/minute")
async def logout_all(request: Request, claims: dict = Depends(get_current_claims)):
    business = await get_auth_service(request)
    if not claims.get("sub"):
        raise HTTPException(400, "No user id")
    await business.logout_all_sessions(claims["sub"])
    return JSONResponse({"status": "ok", "message": "All sessions terminated"})


@router.get("/auth/me", response_model=MeResponseDTO)
@limiter.limit("20/minute")
async def me(request: Request, claims: dict = Depends(get_current_claims)):
    try:
        business = await get_auth_service(request)
        return MeResponseDTO(**business.me_payload(claims))
    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")