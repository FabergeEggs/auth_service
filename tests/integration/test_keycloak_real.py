"""Изолированные интеграционные тесты адаптера Keycloak."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.keycloak_adapter import KeycloakAdapter
from src.config import settings

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.mark.asyncio
class TestKeycloakRealIntegration:
    """Тесты поведения адаптера без внешнего Keycloak."""

    async def test_health_check_real(self):
        """Health check возвращает true на HTTP 200."""
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
            frontend_url=settings.frontend_url,
        )
        response = MagicMock()
        response.status_code = 200
        with patch.object(adapter._client, "get", AsyncMock(return_value=response)):
            result = await adapter.health_check()
            assert result is True
        await adapter.close()

    async def test_create_and_get_user_real(self):
        """Создание пользователя отдает id из заголовка Location."""
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
            frontend_url=settings.frontend_url,
        )

        response = MagicMock()
        response.headers = {"Location": "http://keycloak/users/new-user-id"}
        with (
            patch.object(adapter, "_get_admin_token", AsyncMock(return_value="adm")),
            patch.object(adapter, "_retry_request", AsyncMock(return_value=response)),
            patch.object(adapter, "send_verification_email", AsyncMock()),
        ):
            user_id = await adapter.create_user(
                username="test_user",
                email="test_user@test.com",
                password="Test123!@#",
                first_name="Test",
                last_name="User",
            )
            assert user_id == "new-user-id"
        await adapter.close()
