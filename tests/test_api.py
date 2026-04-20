import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from src.config import settings
from src.service.auth_service import AuthService
from src.adapters.keycloak_adapter import KeycloakAdapter

@pytest_asyncio.fixture
async def client():
    """HTTP клиент для тестирования API"""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as ac:
        yield ac

@pytest_asyncio.fixture
async def auth_service_mock():
    """Мок AuthService для API тестов"""
    from unittest.mock import AsyncMock
    mock = AsyncMock(spec=AuthService)
    mock.register = AsyncMock(return_value="test-user-id")
    mock.login = AsyncMock(return_value={
        "access_token": "test-token",
        "refresh_token": "test-refresh",
        "expires_in": 300,
        "user_id": "test-user-id"
    })
    mock.verify_email = AsyncMock()
    mock.forgot_password = AsyncMock()
    mock.reset_password = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def authenticated_client(client, mock_token_claims):
    """Аутентифицированный HTTP клиент"""
    # Добавляем заголовок Authorization
    client.headers["Authorization"] = "Bearer test-token"
    
    # Мокаем верификацию токена
    app.state.token_verifier = AsyncMock()
    app.state.token_verifier.verify = AsyncMock(return_value=mock_token_claims)
    
    yield client
    
    # Очищаем заголовки
    client.headers.pop("Authorization", None)