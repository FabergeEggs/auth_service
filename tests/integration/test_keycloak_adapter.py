from src.adapters.keycloak_adapter import KeycloakAdapter
from src.config import settings
from unittest.mock import patch, AsyncMock
import pytest


class TestKeycloakAdapterHealthCheck:
    @pytest.fixture
    def adapter(self):
        """Создаем адаптер для тестов"""
        return KeycloakAdapter.from_settings(settings)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter):
        """Проверка health check на здоровом сервере"""
        with patch.object(adapter._client, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, adapter):
        """Проверка health check на нездоровом сервере"""
        with patch.object(adapter._client, "get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await adapter.health_check()
            assert result is False
