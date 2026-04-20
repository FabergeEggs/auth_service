mport asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from faker import Faker
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from src.service.auth_service import AuthService
from src.adapters.keycloak_adapter import KeycloakAdapter

# Инициализируем Faker
fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client():
    """HTTP клиент для тестирования API"""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as ac:
        yield ac

@pytest.fixture
def mock_auth_provider():
    """Мок провайдера аутентификации"""
    mock = AsyncMock()
    mock.create_user = AsyncMock(return_value="test-user-id-123")
    mock.get_user_by_username = AsyncMock(return_value=None)
    mock.login_with_username = AsyncMock(return_value={
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 300,
        "refresh_expires_in": 2592000,
        "token_type": "bearer"
    })
    mock.refresh_token = AsyncMock(return_value={
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 300
    })
    mock.logout = AsyncMock()
    mock.logout_all_sessions = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.send_reset_password_email = AsyncMock()
    mock.reset_password_with_action_token = AsyncMock()
    mock.send_verification_email = AsyncMock()
    mock.verify_email = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Тестовые данные пользователя"""
    return {
        "email": "test@example.com",
        "password": "Test123!@#",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890",
        "about": "Test user"
    }

@pytest.fixture
def test_login_data(test_user_data) -> Dict[str, str]:
    """Данные для логина"""
    return {
        "login": test_user_data["email"],
        "password": test_user_data["password"]
    }

@pytest.fixture
def mock_token_claims() -> Dict[str, Any]:
    """Мок claims из JWT токена"""
    from datetime import datetime, timedelta
    
    return {
        "sub": "test-user-id-123",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "email_verified": True,
        "realm_access": {
            "roles": ["user"]
        },
        "resource_access": {
            "auth-service": {
                "roles": ["user"]
            }
        },
        "attributes": {
            "phone": ["+1234567890"],
            "about": ["Test about me"]
        },
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "iss": "http://keycloak:8080/realms/myrealm",
        "aud": "auth-service"
    }