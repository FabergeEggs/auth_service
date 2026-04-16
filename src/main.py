import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.adapters.keycloak_adapter import KeycloakAdapter, TokenVerifier
from src.service.auth_service import AuthService
from src.api.handlers import router, limiter
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация адаптеров
    adapter = KeycloakAdapter(
        token_url=settings.token_url,
        logout_url=settings.logout_url,
        admin_users_url=settings.admin_users_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        admin_username=settings.admin_username,
        admin_password=settings.admin_password,
        admin_client_id=settings.admin_client_id,
        admin_token_url=settings.admin_token_url,
        realm=settings.realm,
        frontend_url=settings.frontend_url
    )

    token_verifier = TokenVerifier(
        jwks_url=settings.jwks_url,
        issuer=settings.issuer,
        audience=settings.audience
    )
    auth_service = AuthService(adapter)

    # Сохраняем в app.state
    app.state.auth_service = auth_service
    app.state.token_verifier = token_verifier
    app.state.adapter = adapter

    yield

    # Закрытие клиентов
    try:
        await adapter.close()
    except Exception as e:
        logger.error("Error closing adapter: %s", e)
    try:
        await token_verifier.close()
    except Exception as e:
        logger.error("Error closing token verifier: %s", e)


app = FastAPI(lifespan=lifespan, title="Auth Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Подключаем роутер
app.include_router(router)


@app.get("/health")
async def health_check(request: Request):
    business = await get_auth_service(request)
    ok = await business.health_check()
    if ok:
        return {"status": "healthy", "dependencies": {"keycloak": "ok"}}
    return JSONResponse(
        {"status": "unhealthy", "dependencies": {"keycloak": "down"}},
        status_code=503
    )