import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.api.dto import (
    LoginRequestDTO,
    RegisterRequestDTO,
    RegisterResponseDTO,
    ResetPasswordRequestDTO,
    ForgotPasswordRequestDTO,
    VerifyEmailRequestDTO,
    MeResponseDTO,
    TokenResponseDTO,
)
from src.errors import (
    InvalidTokenError,
    KeycloakError,
    KeycloakUnavailableError,
    UserAlreadyExistsError,
)
from src.service.auth_service import AuthService
from src.config import settings

logger = logging.getLogger("auth_service.api")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1")


async def get_settings(request: Request):
    return request.app.state.settings


async def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_token_verifier(request: Request):
    return request.app.state.token_verifier


async def get_current_claims(
    request: Request, authorization: str = Header(default="")
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    verifier = await get_token_verifier(request)
    try:
        return await verifier.verify(token)
    except ValueError as e:
        raise HTTPException(401, str(e))


async def _extract_user_id_from_token(
    request: Request, access_token: str
) -> str | None:
    """Извлекает user_id (sub) из access_token без запроса к Keycloak."""
    try:
        verifier = await get_token_verifier(request)
        claims = await verifier.verify(access_token)
        return claims.get("sub")
    except Exception:
        logger.warning("Cannot extract user_id from token", exc_info=True)
        return None


@router.post(
    "/auth/register",
    response_model=RegisterResponseDTO,
    status_code=200,
    responses={
        200: {"description": "Successful registration", "model": RegisterResponseDTO},
        400: {"description": "Invalid data"},
        409: {"description": "User already exists"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("3/minute")
async def register(payload: RegisterRequestDTO, request: Request):
    business = await get_auth_service(request)
    try:
        uid = await business.register(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            about=payload.about,
        )
        return RegisterResponseDTO(user_id=uid)
    except UserAlreadyExistsError:
        raise HTTPException(409, "User already exists")
    except HTTPStatusError as e:
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error_description", "")
                logger.warning(f"Keycloak error response: {error_msg}")

                if "password" in error_msg.lower():
                    raise HTTPException(400, "Invalid password policy")
                raise HTTPException(400, f"Registration failed: {error_msg}")
            except (ValueError, AttributeError, TypeError) as parse_err:
                logger.warning(
                    f"Keycloak returned 400 but response is not JSON: {e.response.text}, error: {parse_err}"
                )
                if e.response.text and "password" in e.response.text.lower():
                    raise HTTPException(400, "Invalid password policy")
                raise HTTPException(400, "Registration failed: invalid data")
        raise HTTPException(e.response.status_code, "Registration failed")


@router.post(
    "/auth/login",
    response_model=TokenResponseDTO,
    responses={
        200: {"description": "Successful login", "model": TokenResponseDTO},
        401: {"description": "Invalid credentials"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, payload: LoginRequestDTO):
    business = await get_auth_service(request)

    try:
        data = await business.login(login=payload.login, password=payload.password)
        logger.info(
            "Login success",
            extra={"event": "login_success", "user_id": data.get("user_id")},
        )

        token_response = TokenResponseDTO(
            access_token=data["access_token"],
            expires_in=data["expires_in"],
            refresh_expires_in=data.get("refresh_expires_in"),
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope"),
            user_id=data.get("user_id"),
        )

        max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
        response.set_cookie(
            key="refresh_token",
            value=data["refresh_token"],
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            max_age=max_age,
            path="/",
            domain=settings.cookie_domain,
        )

        return token_response

    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")
    except HTTPStatusError:
        logger.warning("Login failed")
        raise HTTPException(401, "Invalid credentials")


@router.post(
    "/auth/refresh",
    response_model=TokenResponseDTO,
    responses={
        200: {"description": "Token refreshed", "model": TokenResponseDTO},
        401: {"description": "Invalid refresh token"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("10/minute")
async def refresh(request: Request, response: Response):
    """
    Обновляет access_token по refresh_token из httpOnly cookie.

    Возвращает новый access_token и метаданные в теле ответа.
    Если Keycloak выдал новый refresh_token — обновляет cookie.
    user_id извлекается из нового access_token локально, без запроса к Keycloak.
    """
    business = await get_auth_service(request)
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(401, "No refresh token")

    try:
        data = await business.refresh(token)

        # Извлекаем user_id из нового access_token (локальная верификация JWT)
        user_id = None
        if "access_token" in data:
            user_id = await _extract_user_id_from_token(request, data["access_token"])

        token_response = TokenResponseDTO(
            access_token=data["access_token"],
            expires_in=data["expires_in"],
            refresh_expires_in=data.get("refresh_expires_in"),
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope"),
            user_id=user_id,
        )

        # Keycloak может вернуть новый refresh_token (token rotation)
        if "refresh_token" in data:
            max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
            response.set_cookie(
                key="refresh_token",
                value=data["refresh_token"],
                httponly=True,
                secure=settings.secure_cookies,
                samesite="lax",
                max_age=max_age,
                path="/",
            )

        return token_response

    except HTTPStatusError:
        response.delete_cookie(
            key="refresh_token",
            path="/",
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
        )
        raise HTTPException(401, "Invalid refresh token")

    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")


@router.post(
    "/auth/logout",
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {"application/json": {"example": {"status": "ok"}}},
        },
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("5/minute")
async def logout(request: Request, response: Response):
    """
    Завершает сессию: отзывает refresh_token в Keycloak и удаляет cookie.
    """
    business = await get_auth_service(request)
    token = request.cookies.get("refresh_token")

    if token:
        try:
            await business.logout(token)
        except HTTPStatusError:
            pass
        except KeycloakUnavailableError:
            raise HTTPException(503, "Authentication service temporarily unavailable")
        finally:
            response.delete_cookie(
                key="refresh_token",
                path="/",
                httponly=True,
                secure=settings.secure_cookies,
                samesite="lax",
            )

    return {"status": "ok"}


@router.post(
    "/auth/logout-all",
    responses={
        200: {
            "description": "All sessions terminated",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "message": "All sessions terminated"}
                }
            },
        },
        400: {"description": "No user id"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("5/minute")
async def logout_all(request: Request, claims: dict = Depends(get_current_claims)):
    """Завершает все сессии пользователя во всех устройствах."""
    business = await get_auth_service(request)
    if not claims.get("sub"):
        raise HTTPException(400, "No user id")
    await business.logout_all_sessions(claims["sub"])
    return JSONResponse({"status": "ok", "message": "All sessions terminated"})


@router.post(
    "/auth/verify-email",
    responses={
        200: {
            "description": "Email verified",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Email verified successfully. You can now login."
                    }
                }
            },
        },
        400: {"description": "Invalid token"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("5/minute")
async def verify_email(payload: VerifyEmailRequestDTO, request: Request):
    """Подтверждение email по токену из письма."""
    logger.info(f"Received token: {payload.key[:50]}...")
    business = await get_auth_service(request)
    try:
        await business.verify_email(payload.key)
        return {"message": "Email verified successfully. You can now login."}
    except InvalidTokenError as e:
        logger.warning(f"Invalid verification token: {e}")
        raise HTTPException(400, str(e))
    except KeycloakError as e:
        logger.error(f"Keycloak error during verification: {e}")
        raise HTTPException(503, "Verification service temporarily unavailable")
    except Exception as e:
        logger.error(f"Email verification failed: {e}", exc_info=True)
        raise HTTPException(500, "Verification failed")


@router.post(
    "/auth/reset-password",
    responses={
        200: {
            "description": "Password reset",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password has been reset successfully. You can now login with your new password."
                    }
                }
            },
        },
        400: {"description": "Invalid token or password"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("5/minute")
async def reset_password(payload: ResetPasswordRequestDTO, request: Request):
    """
    Завершает сброс пароля, используя одноразовый ключ (action token).
    """
    business = await get_auth_service(request)
    try:
        await business.reset_password(payload.key, payload.new_password)
        return {
            "message": "Password has been reset successfully. You can now login with your new password."
        }
    except InvalidTokenError as e:
        logger.warning(f"Invalid reset token: {e}")
        raise HTTPException(400, str(e))
    except ValueError as e:
        logger.warning(f"Invalid password: {e}")
        raise HTTPException(400, str(e))
    except KeycloakError as e:
        logger.error(f"Keycloak error during password reset: {e}")
        raise HTTPException(503, "Password reset service temporarily unavailable")
    except Exception as e:
        logger.error(f"Password reset failed: {e}", exc_info=True)
        raise HTTPException(500, "Password reset failed")


@router.post(
    "/auth/forgot-password",
    responses={
        200: {
            "description": "Reset email sent",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If the email exists, a password reset link has been sent"
                    }
                }
            },
        },
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("3/minute")
async def forgot_password(payload: ForgotPasswordRequestDTO, request: Request):
    """
    Инициирует сброс пароля: отправляет пользователю письмо со ссылкой на фронтенд.
    """
    business = await get_auth_service(request)
    try:
        await business.forgot_password(payload.email)
        return {"message": "If the email exists, a password reset link has been sent"}
    except KeycloakUnavailableError:
        logger.error("Keycloak unavailable during forgot password")
        raise HTTPException(503, "Authentication service temporarily unavailable")
    except Exception as e:
        logger.error(f"Forgot password failed: {e}", exc_info=True)
        raise HTTPException(500, "Internal error")


@router.post(
    "/auth/password-change",
    responses={
        200: {
            "description": "Change link sent",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password change link has been sent to your email"
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("3/minute")
async def password_change(request: Request, claims: dict = Depends(get_current_claims)):
    """Отправляет ссылку на смену пароля авторизованному пользователю."""
    try:
        email = claims.get("email")
        if not email:
            raise HTTPException(400, "Email not found in token")

        business = await get_auth_service(request)
        await business.forgot_password(email)
        return {"message": "Password change link has been sent to your email"}
    except KeycloakUnavailableError:
        raise HTTPException(503, "Service temporarily unavailable")


@router.get(
    "/auth/me",
    response_model=MeResponseDTO,
    responses={
        200: {"description": "User information", "model": MeResponseDTO},
        401: {"description": "Invalid or missing token"},
        500: {"description": "Internal server error"},
    },
)
async def get_me(request: Request, claims: dict = Depends(get_current_claims)):
    """Возвращает информацию о текущем пользователе."""
    try:
        business = await get_auth_service(request)
        payload = business.me_payload(claims)
        return MeResponseDTO(**payload)
    except ValueError as e:
        logger.error(f"Invalid claims in /auth/me: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    except TypeError as e:
        logger.error(f"Type error in /auth/me: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error in /auth/me: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get user information")
