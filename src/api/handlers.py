# import logging
# from fastapi import APIRouter, Depends, Header, HTTPException, Request
# from fastapi.responses import JSONResponse
# from httpx import HTTPStatusError
# from slowapi import Limiter
# from slowapi.util import get_remote_address
# from src.api.dto import (
#     LoginRequestDTO,
#     RegisterRequestDTO,
#     RegisterResponseDTO,
#     ResetPasswordRequestDTO,
#     ForgotPasswordRequestDTO,
#     VerifyEmailRequestDTO,
#     MeResponseDTO
# )
# from src.errors import (
#     InvalidTokenError,
#     KeycloakError,
#     KeycloakUnavailableError,
#     UserAlreadyExistsError,
# )
# from src.service.auth_service import AuthService
# from src.config import settings

# logger = logging.getLogger("auth_service.api")
# limiter = Limiter(key_func=get_remote_address)

# router = APIRouter(prefix="/api/v1")

# async def get_settings(request: Request):
#     return request.app.state.settings

# async def get_auth_service(request: Request) -> AuthService:
#     return request.app.state.auth_service


# async def get_token_verifier(request: Request):
#     return request.app.state.token_verifier


# async def get_current_claims(
#     request: Request,   
#     authorization: str = Header(default="")
# ) -> dict:
#     if not authorization.startswith("Bearer "):
#         raise HTTPException(401, "Missing bearer token")
#     token = authorization.removeprefix("Bearer ").strip()
#     verifier = await get_token_verifier(request)
#     try:
#         return await verifier.verify(token)
#     except ValueError as e:
#         raise HTTPException(401, str(e))


# @router.post("/auth/register", response_model=RegisterResponseDTO)
# @limiter.limit("3/minute")
# async def register(payload: RegisterRequestDTO, request: Request):
#     business = await get_auth_service(request)
#     try:
#         uid = await business.register(
#             email=payload.email, password=payload.password,
#             first_name=payload.first_name, last_name=payload.last_name,
#             phone=payload.phone, about=payload.about
#         )
#         return RegisterResponseDTO(user_id=uid)
#     except UserAlreadyExistsError:
#         raise HTTPException(409, "User already exists")
#     except HTTPStatusError as e:
#         if e.response.status_code == 400:
#             try:
#                 error_data = e.response.json()
#                 error_msg = error_data.get("error_description", "Invalid password policy")
#                 raise HTTPException(400, f"Registration failed: {error_msg}")
#             except Exception:
#                 logger.warning("Keycloak returned 400 but response is not JSON: %s", e.response.text)
#                 raise HTTPException(400, "Registration failed: invalid data")
#         raise HTTPException(e.response.status_code, "Registration failed")
#     except KeycloakUnavailableError:
#         raise HTTPException(503, "Authentication service temporarily unavailable")
#     except Exception:
#         logger.exception("Unexpected register error")
#         raise HTTPException(500, "Internal error")


# @router.post("/auth/login")
# @limiter.limit("5/minute")
# async def login(request: Request, payload: LoginRequestDTO):
#     business = await get_auth_service(request)
#     settings = await get_settings(request)
    
#     try:
#         data = await business.login(login=payload.login, password=payload.password)
#         logger.info("Login success", extra={"event": "login_success", "user_id": data.get("user_id")})
        
#         resp = JSONResponse({
#             "access_token": data["access_token"],
#             "expires_in": data["expires_in"],
#             "refresh_expires_in": data.get("refresh_expires_in"),
#             "token_type": data.get("token_type", "bearer"),
#             "scope": data.get("scope"),
#             "user_id": data.get("user_id") 
#         })
        
#         max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
#         resp.set_cookie(
#             "refresh_token", 
#             data["refresh_token"],
#             httponly=True, 
#             secure=settings.secure_cookies, 
#             samesite="lax",
#             max_age=max_age, 
#             path="/",
#             domain=settings.cookie_domain
#         )
#         return resp
#     except KeycloakUnavailableError:
#         raise HTTPException(503, "Authentication service temporarily unavailable")
#     except HTTPStatusError:
#         logger.warning("Login failed")
#         raise HTTPException(401, "Invalid credentials")


# @router.post("/auth/refresh")
# @limiter.limit("10/minute")
# async def refresh(request: Request):
#     business = await get_auth_service(request)
#     token = request.cookies.get("refresh_token")
#     if not token:
#         raise HTTPException(401, "No refresh token")
#     try:
#         data = await business.refresh(token)
#         resp = JSONResponse({
#             "access_token": data["access_token"],
#             "expires_in": data["expires_in"],
#             "refresh_expires_in": data.get("refresh_expires_in"),
#             "token_type": data.get("token_type", "bearer"),
#             "scope": data.get("scope")
#         })
#         if "refresh_token" in data:
#             max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
#             is_production = (settings.environment == "production")
#             resp.set_cookie(
#                 "refresh_token", data["refresh_token"],
#                 httponly=True, secure=is_production, samesite="lax",
#                 max_age=max_age, path="/"
#             )
#         return resp
#     except HTTPStatusError:
#         resp = JSONResponse({"detail": "Invalid refresh token"}, status_code=401)
#         is_production = (settings.environment == "production")
#         resp.delete_cookie(
#             "refresh_token", path="/",
#             httponly=True, secure=is_production, samesite="lax"
#         )
#         return resp
#     except KeycloakUnavailableError:
#         raise HTTPException(503, "Authentication service temporarily unavailable")

# @router.post("/auth/logout")
# @limiter.limit("5/minute")
# async def logout(request: Request):
#     business = await get_auth_service(request)
#     token = request.cookies.get("refresh_token")
#     resp = JSONResponse({"status": "ok"})
#     if token:
#         try:
#             await business.logout(token)
#         except HTTPStatusError:
#             pass
#         except KeycloakUnavailableError:
#             raise HTTPException(503, "Authentication service temporarily unavailable")
#         finally:
#             is_production = (settings.environment == "production")
#             resp.delete_cookie(
#                 "refresh_token", path="/",
#                 httponly=True, secure=is_production, samesite="lax"
#             )
#     return resp


# @router.post("/auth/logout-all")
# @limiter.limit("5/minute")
# async def logout_all(request: Request, claims: dict = Depends(get_current_claims)):
#     business = await get_auth_service(request)
#     if not claims.get("sub"):
#         raise HTTPException(400, "No user id")
#     await business.logout_all_sessions(claims["sub"])
#     return JSONResponse({"status": "ok", "message": "All sessions terminated"})

# @router.post("/auth/verify-email")
# @limiter.limit("5/minute")
# async def verify_email(payload: VerifyEmailRequestDTO, request: Request):
#     """Подтверждение email по токену из письма"""
#     business = await get_auth_service(request)
#     try:
#         await business.verify_email(payload.key)
#         return {"message": "Email verified successfully. You can now login."}
#     except InvalidTokenError as e:
#         logger.warning(f"Invalid verification token: {e}")
#         raise HTTPException(400, str(e))
#     except KeycloakError as e:
#         logger.error(f"Keycloak error during verification: {e}")
#         raise HTTPException(503, "Verification service temporarily unavailable")
#     except Exception as e:
#         logger.error(f"Email verification failed: {e}", exc_info=True)
#         raise HTTPException(500, "Verification failed")


# @router.post("/auth/reset-password")
# @limiter.limit("5/minute")
# async def reset_password(payload: ResetPasswordRequestDTO, request: Request):
#     """
#     Завершает сброс пароля, используя одноразовый ключ (action token).
#     """
#     business = await get_auth_service(request)
#     try:
#         await business.reset_password(payload.key, payload.new_password)
#         return {"message": "Password has been reset successfully. You can now login with your new password."}
#     except InvalidTokenError as e:
#         logger.warning(f"Invalid reset token: {e}")
#         raise HTTPException(400, str(e))
#     except ValueError as e:
#         logger.warning(f"Invalid password: {e}")
#         raise HTTPException(400, str(e))
#     except KeycloakError as e:
#         logger.error(f"Keycloak error during password reset: {e}")
#         raise HTTPException(503, "Password reset service temporarily unavailable")
#     except Exception as e:
#         logger.error(f"Password reset failed: {e}", exc_info=True)
#         raise HTTPException(500, "Password reset failed")


# @router.post("/auth/forgot-password")
# @limiter.limit("3/minute")
# async def forgot_password(payload: ForgotPasswordRequestDTO, request: Request):
#     """
#     Инициирует сброс пароля: отправляет пользователю письмо со ссылкой на фронтенд.
#     """
#     business = await get_auth_service(request)
#     await business.forgot_password(payload.email)
#     return {"message": "If the email exists, a password reset link has been sent"}

# @router.get("/auth/me", response_model=MeResponseDTO)
# async def get_me(
#     request: Request, 
#     claims: dict = Depends(get_current_claims)
# ):
#     try:
#         business = await get_auth_service(request)
#         payload = business.me_payload(claims)
#         return MeResponseDTO(**payload)
        
#     except ValueError as e:
#         logger.error(f"Invalid claims in /auth/me: {e}")
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid authentication data"
#         )
#     except TypeError as e:
#         logger.error(f"Type error in /auth/me: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail="Internal server error"
#         )
#     except Exception as e:
#         logger.error(f"Unexpected error in /auth/me: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to get user information"
#         )


import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    TokenResponseDTO
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


@router.post(
    "/auth/register", 
    response_model=RegisterResponseDTO,
    status_code=200,
    responses={
        200: {"description": "Successful registration", "model": RegisterResponseDTO},
        400: {"description": "Invalid data"},
        409: {"description": "User already exists"},
        503: {"description": "Service unavailable"}
    }
)
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


@router.post(
    "/auth/login",
    response_model=TokenResponseDTO,
    responses={
        200: {"description": "Successful login", "model": TokenResponseDTO},
        401: {"description": "Invalid credentials"},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequestDTO):
    business = await get_auth_service(request)
    settings = await get_settings(request)
    
    try:
        data = await business.login(login=payload.login, password=payload.password)
        logger.info("Login success", extra={"event": "login_success", "user_id": data.get("user_id")})
        
        response_data = {
            "access_token": data["access_token"],
            "expires_in": data["expires_in"],
            "refresh_expires_in": data.get("refresh_expires_in"),
            "token_type": data.get("token_type", "bearer"),
            "scope": data.get("scope"),
            "user_id": data.get("user_id")
        }
        
        resp = JSONResponse(response_data)
        
        max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
        resp.set_cookie(
            "refresh_token", 
            data["refresh_token"],
            httponly=True, 
            secure=settings.secure_cookies, 
            samesite="lax",
            max_age=max_age, 
            path="/",
            domain=settings.cookie_domain
        )
        return resp
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
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("10/minute")
async def refresh(request: Request):
    business = await get_auth_service(request)
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        data = await business.refresh(token)
        response_data = {
            "access_token": data["access_token"],
            "expires_in": data["expires_in"],
            "refresh_expires_in": data.get("refresh_expires_in"),
            "token_type": data.get("token_type", "bearer"),
            "scope": data.get("scope")
        }
        resp = JSONResponse(response_data)
        if "refresh_token" in data:
            max_age = data.get("refresh_expires_in", settings.refresh_token_max_age)
            is_production = (settings.environment == "production")
            resp.set_cookie(
                "refresh_token", data["refresh_token"],
                httponly=True, secure=is_production, samesite="lax",
                max_age=max_age, path="/"
            )
        return resp
    except HTTPStatusError:
        resp = JSONResponse({"detail": "Invalid refresh token"}, status_code=401)
        is_production = (settings.environment == "production")
        resp.delete_cookie(
            "refresh_token", path="/",
            httponly=True, secure=is_production, samesite="lax"
        )
        return resp
    except KeycloakUnavailableError:
        raise HTTPException(503, "Authentication service temporarily unavailable")


@router.post(
    "/auth/logout",
    responses={
        200: {"description": "Successfully logged out", "content": {"application/json": {"example": {"status": "ok"}}}},
        503: {"description": "Service unavailable"}
    }
)
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
                "refresh_token", path="/",
                httponly=True, secure=is_production, samesite="lax"
            )
    return resp


@router.post(
    "/auth/logout-all",
    responses={
        200: {"description": "All sessions terminated", "content": {"application/json": {"example": {"status": "ok", "message": "All sessions terminated"}}}},
        400: {"description": "No user id"},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("5/minute")
async def logout_all(request: Request, claims: dict = Depends(get_current_claims)):
    business = await get_auth_service(request)
    if not claims.get("sub"):
        raise HTTPException(400, "No user id")
    await business.logout_all_sessions(claims["sub"])
    return JSONResponse({"status": "ok", "message": "All sessions terminated"})


@router.post(
    "/auth/verify-email",
    responses={
        200: {"description": "Email verified", "content": {"application/json": {"example": {"message": "Email verified successfully. You can now login."}}}},
        400: {"description": "Invalid token"},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("5/minute")
async def verify_email(payload: VerifyEmailRequestDTO, request: Request):
    """Подтверждение email по токену из письма"""
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
        200: {"description": "Password reset", "content": {"application/json": {"example": {"message": "Password has been reset successfully. You can now login with your new password."}}}},
        400: {"description": "Invalid token or password"},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("5/minute")
async def reset_password(payload: ResetPasswordRequestDTO, request: Request):
    """
    Завершает сброс пароля, используя одноразовый ключ (action token).
    """
    business = await get_auth_service(request)
    try:
        await business.reset_password(payload.key, payload.new_password)
        return {"message": "Password has been reset successfully. You can now login with your new password."}
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
        200: {"description": "Reset email sent", "content": {"application/json": {"example": {"message": "If the email exists, a password reset link has been sent"}}}},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("3/minute")
async def forgot_password(payload: ForgotPasswordRequestDTO, request: Request):
    """
    Инициирует сброс пароля: отправляет пользователю письмо со ссылкой на фронтенд.
    """
    business = await get_auth_service(request)
    await business.forgot_password(payload.email)
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post(
    "/auth/password-change",
    responses={
        200: {"description": "Change link sent", "content": {"application/json": {"example": {"message": "Password change link has been sent to your email"}}}},
        401: {"description": "Not authenticated"},
        503: {"description": "Service unavailable"}
    }
)
@limiter.limit("3/minute")
async def request_password_change(
    request: Request,
    claims: dict = Depends(get_current_claims)
):
    """
    Запрос на смену пароля для ЗАЛОГИНЕННОГО пользователя.
    Отправляет письмо с Action Token.
    """
    email = claims.get("email")
    
    if not email:
        raise HTTPException(401, "Email not found in token")
    payload = ForgotPasswordRequestDTO(email=str(email))
    
    business = await get_auth_service(request)
    await business.forgot_password(payload.email)
    
    return {"message": "Password change link has been sent to your email"}

@router.get(
    "/auth/me", 
    response_model=MeResponseDTO,
    responses={
        200: {"description": "User information", "model": MeResponseDTO},
        401: {"description": "Invalid or missing token"},
        500: {"description": "Internal server error"}
    }
)
async def get_me(
    request: Request, 
    claims: dict = Depends(get_current_claims)
):
    """Возвращает информацию о текущем пользователе"""
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
