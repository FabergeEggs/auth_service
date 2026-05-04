# tests/conftest.py
import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from main import app
from src.service.auth_service import AuthService
from src.config import settings
from tests.mocks import MockAuthProvider


# Автоматическая маркировка тестов
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


def pytest_runtest_setup(item):
    """Автоматически применяем маркеры на основе пути"""
    if "integration" in str(item.fspath):
        item.add_marker(pytest.mark.integration)
    elif "unit" in str(item.fspath):
        item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="session")
def event_loop():
    """Создаёт event loop для всей сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    from datetime import datetime, UTC, timedelta

    now = datetime.now(UTC)
    return {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {"roles": ["user"]},
        "resource_access": {"account": {"roles": ["view-profile"]}},
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
    }


@pytest.fixture
async def client():
    """Тестовый клиент FastAPI"""
    app.state.settings = MagicMock(
        refresh_token_max_age=2592000,
        secure_cookies=False,
        cookie_domain=None,
        environment="test",
    )
    app.state.auth_service = AsyncMock(spec=AuthService)
    app.state.token_verifier = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(client, mock_token_claims):
    """Аутентифицированный клиент"""
    client.headers["Authorization"] = "Bearer test-token"
    app.state.token_verifier.verify = AsyncMock(return_value=mock_token_claims)
    yield client
    client.headers.pop("Authorization", None)


@pytest.fixture
def mock_event_producer():
    """Мок для Kafka producer"""
    mock = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.send_event = AsyncMock()
    return mock


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Тестовые данные пользователя"""
    try:
        from faker import Faker

        fake = Faker()
        return {
            "email": fake.email(),
            "password": "Test123!@#",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number()[:20],
            "about": fake.text(max_nb_chars=100),
        }
    except ImportError:
        return {
            "email": "test@example.com",
            "password": "Test123!@#",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "about": "Test about me",
        }


@pytest.fixture
def test_login_data(test_user_data) -> Dict[str, str]:
    """Тестовые данные для логина"""
    return {"login": test_user_data["email"], "password": test_user_data["password"]}


@pytest.fixture
def mock_token_claims() -> Dict[str, Any]:
    """Mock JWT claims"""
    from datetime import datetime, UTC, timedelta

    now = datetime.now(UTC)
    return {
        "sub": "test-user-id-123",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "email_verified": True,
        "realm_access": {"roles": ["user"]},
        "resource_access": {"auth-service": {"roles": ["user"]}},
        "attributes": {"phone": ["+1234567890"], "about": ["Test about me"]},
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": f"{settings.keycloak_url}/realms/{settings.realm}",
        "aud": settings.client_id,
    }
