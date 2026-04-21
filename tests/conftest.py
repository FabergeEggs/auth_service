"""Общие фикстуры для всех тестов"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import UTC, datetime, timedelta
import pytest
import pytest_asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

# Теперь импорты должны работать
from main import app
from src.service.auth_service import AuthService


import pytest
from src.service.auth_service import AuthService
from tests.mocks import MockAuthProvider

@pytest.fixture
def mock_auth_provider():
    """Мок для AuthProvider"""
    return MockAuthProvider()

@pytest.fixture
def auth_service(mock_auth_provider):
    """Фикстура AuthService с моком"""
    return AuthService(auth_provider=mock_auth_provider)

@pytest.fixture
def sample_claims():
    """Пример claims для тестов"""
    return {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {"roles": ["user"]},
        "resource_access": {
            "account": {"roles": ["view-profile"]}
        }
    }
# Инициализируем Faker (если установлен)
try:
    from faker import Faker
    fake = Faker()
except ImportError:
    # Fallback если faker не установлен
    class FakeFallback:
        def email(self): return "test@example.com"
        def first_name(self): return "Test"
        def last_name(self): return "User"
        def phone_number(self): return "+1234567890"
        def text(self, max_nb_chars=100): return "Test text"
    fake = FakeFallback()

@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client():
    """HTTP клиент для тестирования API"""
    app.state.settings = MagicMock(
        refresh_token_max_age=2592000,
        secure_cookies=False,
        cookie_domain=None,
        environment="test",
    )
    app.state.auth_service = AsyncMock(spec=AuthService)
    app.state.token_verifier = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client, mock_token_claims):
    """Аутентифицированный HTTP клиент"""
    client.headers["Authorization"] = "Bearer test-token"
    app.state.token_verifier.verify = AsyncMock(return_value=mock_token_claims)
    yield client
    client.headers.pop("Authorization", None)

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
def mock_event_producer():
    """Мок Kafka продюсера"""
    mock = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.send_event = AsyncMock()
    return mock

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Тестовые данные пользователя"""
    return {
        "email": fake.email(),
        "password": "Test123!@#",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "phone": fake.phone_number()[:20],
        "about": fake.text(max_nb_chars=100)
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
    now = datetime.now(UTC)

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
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": "http://keycloak:8080/realms/myrealm",
        "aud": "auth-service"
    }

@pytest.fixture
def authenticated_client_with_email(client, mock_token_claims):
    """Аутентифицированный клиент с email в токене"""
    client.headers["Authorization"] = "Bearer test-token"
    app.state.token_verifier.verify = AsyncMock(return_value=mock_token_claims)
    yield client
    client.headers.pop("Authorization", None)