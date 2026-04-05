import logging
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware   # <-- добавлен импорт
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError

from src.adapters.keycloak_adapter import KeycloakConflictError, TokenVerifier
from src.api.dto import (
    LoginRequestDTO,
    LogoutRequestDTO,
    MeResponseDTO,
    RefreshTokenDTO,
    RegisterRequestDTO,
    RegisterResponseDTO,
    TokenResponseDTO,
    ChangeEmailRequestDTO
)
from src.service.auth_service import AuthService

logger = logging.getLogger("auth_service.api")

def create_app(auth_service: AuthService, token_verifier: TokenVerifier) -> FastAPI:
    app = FastAPI(title="Auth Service")

    # Настройка CORS – теперь здесь
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # или ["*"] для разработки
        allow_credentials=True,
        allow_methods=["*"],        # вместо ошибочного URL
        allow_headers=["*"],        # вместо ошибочного URL
    )

    async def get_current_claims(authorization: str = Header(default="")) -> dict:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        return await token_verifier.verify(token)

    def get_auth_service() -> AuthService:
        return auth_service

    @app.post("/auth/register", response_model=RegisterResponseDTO)
    async def register(
        payload: RegisterRequestDTO,
        business: AuthService = Depends(get_auth_service),
    ) -> RegisterResponseDTO:
        try:
            user_id = await business.register(
                email=payload.email,
                password=payload.password,
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone,
                about=payload.about,
            )
            return RegisterResponseDTO(user_id=user_id)
        except KeycloakConflictError:
            raise HTTPException(status_code=409, detail="User already exists")
        except HTTPStatusError as exc:
            logger.warning("Registration failed: %s", exc.response.text)
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Registration failed: {exc.response.text}",
            )
        except Exception:
            logger.exception("Unexpected registration error")
            raise HTTPException(status_code=500, detail="Internal error")

    @app.post("/auth/login", response_model=TokenResponseDTO)
    async def login(
        payload: LoginRequestDTO,
        business: AuthService = Depends(get_auth_service),
    ) -> TokenResponseDTO:
        try:
            data = await business.login(login=payload.login, password=payload.password)
            return TokenResponseDTO(**data)
        except HTTPStatusError as exc:
            detail = "Invalid credentials"
            try:
                err = exc.response.json()
                if isinstance(err, dict) and err.get("error_description"):
                    detail = f"Invalid credentials ({err.get('error', 'error')}: {err['error_description']})"
            except Exception:
                pass
            raise HTTPException(status_code=401, detail=detail)

    @app.post("/auth/refresh", response_model=TokenResponseDTO)
    async def refresh(
        payload: RefreshTokenDTO,
        business: AuthService = Depends(get_auth_service),
    ) -> TokenResponseDTO:
        try:
            data = await business.refresh(payload.refresh_token)
            return TokenResponseDTO(**data)
        except HTTPStatusError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

    @app.post("/auth/logout")
    async def logout(
        payload: LogoutRequestDTO,
        business: AuthService = Depends(get_auth_service),
    ) -> JSONResponse:
        try:
            await business.logout(payload.refresh_token)
            return JSONResponse({"status": "ok"})
        except HTTPStatusError:
            raise HTTPException(status_code=400, detail="Logout failed")
        
    @app.post("/auth/change-email")
    async def change_email(
        payload: ChangeEmailRequestDTO,
        claims: dict = Depends(get_current_claims),
        business: AuthService = Depends(get_auth_service),
    ):
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            await business.change_email(user_id, payload.new_email)
            return {"message": "Verification email sent to new address. Please check your inbox."}
        except HTTPStatusError as exc:
            if exc.response.status_code == 409:
                raise HTTPException(status_code=409, detail="Email already in use by another account")
            logger.warning("Email change failed: %s", exc.response.text)
            raise HTTPException(status_code=400, detail="Could not change email")
        except Exception:
            logger.exception("Unexpected error during email change")
            raise HTTPException(status_code=500, detail="Internal error")

    @app.post("/auth/resend-verification")
    async def resend_verification(
        claims: dict = Depends(get_current_claims),
        business: AuthService = Depends(get_auth_service),
    ):
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            await business.resend_verification(user_id)
            return {"message": "Verification email resent. Please check your inbox."}
        except Exception:
            logger.exception("Failed to resend verification email")
            raise HTTPException(status_code=500, detail="Could not resend verification email")

    @app.get("/auth/me", response_model=MeResponseDTO)
    async def me(
        claims: dict = Depends(get_current_claims),
        business: AuthService = Depends(get_auth_service),
    ) -> MeResponseDTO:
        return MeResponseDTO(**business.me_payload(claims))

    @app.get("/health")
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "healthy"})

    return app