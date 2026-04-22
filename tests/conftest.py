import asyncio
from datetime import UTC, datetime, timedelta
import pytest
import pytest_asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import app  # noqa: E402
from src.service.auth_service import AuthService  # noqa: E402
from tests.mocks import MockAuthProvider  # noqa: E402

try:
    from faker import Faker

    fake = Faker()
except ImportError:

    class FakeFallback:
        def email(self):
            return "test@example.com"

        def first_name(self):
            return "Test"

        def last_name(self):
            return "User"

        def phone_number(self):
            return "+1234567890"

        def text(self, max_nb_chars=100):
            return "Test text"

    fake = FakeFallback()


@pytest.fixture(scope="session")
def event_loop():
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
    return {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {"roles": ["user"]},
        "resource_access": {"account": {"roles": ["view-profile"]}},
    }


@pytest_asyncio.fixture
async def client():
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


@pytest_asyncio.fixture
async def authenticated_client(client, mock_token_claims):
    client.headers["Authorization"] = "Bearer test-token"
    app.state.token_verifier.verify = AsyncMock(return_value=mock_token_claims)
    yield client
    client.headers.pop("Authorization", None)


@pytest.fixture
def mock_event_producer():
    mock = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.send_event = AsyncMock()
    return mock


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    return {
        "email": fake.email(),
        "password": "Test123!@#",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "phone": fake.phone_number()[:20],
        "about": fake.text(max_nb_chars=100),
    }


@pytest.fixture
def test_login_data(test_user_data) -> Dict[str, str]:
    return {"login": test_user_data["email"], "password": test_user_data["password"]}


@pytest.fixture
def mock_token_claims() -> Dict[str, Any]:
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
        "iss": "http://keycloak:8080/realms/myrealm",
        "aud": "auth-service",
    }
