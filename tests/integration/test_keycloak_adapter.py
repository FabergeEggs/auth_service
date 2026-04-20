"""Интеграционные тесты для KeycloakAdapter."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from src.adapters.keycloak_adapter import KeycloakAdapter


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def keycloak_adapter():
    """Фикстура адаптера Keycloak для тестов."""
    adapter = KeycloakAdapter(
        token_url="http://keycloak:8080/realms/test/protocol/openid-connect/token",
        logout_url="http://keycloak:8080/realms/test/protocol/openid-connect/logout",
        admin_users_url="http://keycloak:8080/admin/realms/test/users",
        client_id="test-client",
        client_secret="test-secret",
        admin_username="admin",
        admin_password="admin",
        admin_client_id="admin-cli",
        admin_token_url="http://keycloak:8080/realms/master/protocol/openid-connect/token",
        realm="test",
        frontend_url="http://localhost:3000",
    )
    yield adapter
    await adapter.close()


class TestKeycloakAdapterHealthCheck:
    """Тесты health check."""

    async def test_health_check_healthy(self, keycloak_adapter):
        """Тест здорового сервиса."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(keycloak_adapter._client, "get", return_value=mock_response):
            result = await keycloak_adapter.health_check()
            assert result is True

    async def test_health_check_unhealthy(self, keycloak_adapter):
        """Тест нездорового сервиса."""
        with patch.object(
            keycloak_adapter._client,
            "get",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await keycloak_adapter.health_check()
            assert result is False


class TestKeycloakAdapterAdminToken:
    """Тесты получения admin токена."""

    async def test_get_admin_token_success(self, keycloak_adapter):
        """Тест успешного получения admin токена."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "admin-token-123",
            "expires_in": 300,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(keycloak_adapter._client, "post", return_value=mock_response):
            token = await keycloak_adapter._get_admin_token()
            assert token == "admin-token-123"
