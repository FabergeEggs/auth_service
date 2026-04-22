"""Тесты rate limiting"""

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


class TestRateLimiting:
    """Тесты ограничения частоты запросов"""

    async def test_register_rate_limit(self, client, test_user_data):
        """Тест rate limit на регистрацию"""
        with patch("src.api.handlers.get_auth_service") as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.register = AsyncMock(return_value="user-id")
            mock_get_auth.return_value = mock_auth

            responses = []
            for _ in range(4):  # Лимит 3/minute
                response = await client.post(
                    "/api/v1/auth/register", json=test_user_data
                )
                responses.append(response)

            # 4-й должен быть отклонен
            assert responses[3].status_code == 429
