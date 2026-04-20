"""Unit тесты для AuthService"""
import base64
import json
from unittest.mock import AsyncMock

import pytest

from src.errors import AuthProviderConflictError, UserAlreadyExistsError
from src.service.auth_service import AuthService

pytestmark = pytest.mark.asyncio

class TestAuthServiceRegistration:
    """Тесты регистрации"""
    
    async def test_register_success(self, mock_auth_provider, test_user_data):
        """Тест успешной регистрации"""
        mock_auth_provider.get_user_by_username.return_value = None
        mock_auth_provider.create_user.return_value = "new-user-id"
        
        auth_service = AuthService(mock_auth_provider)
        user_id = await auth_service.register(**test_user_data)
        
        assert user_id == "new-user-id"
        mock_auth_provider.create_user.assert_called_once()
    
    async def test_register_user_already_exists(self, mock_auth_provider, test_user_data):
        """Тест регистрации существующего пользователя"""
        mock_auth_provider.get_user_by_username.return_value = {"id": "existing-id"}
        
        auth_service = AuthService(mock_auth_provider)
        
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(**test_user_data)

    async def test_register_retries_after_conflict_and_succeeds(self, mock_auth_provider, test_user_data):
        """Тест повторной попытки после конфликта провайдера."""
        mock_auth_provider.get_user_by_username.side_effect = [None, None]
        mock_auth_provider.create_user.side_effect = [AuthProviderConflictError(), "retry-user-id"]

        auth_service = AuthService(mock_auth_provider)
        user_id = await auth_service.register(**test_user_data)

        assert user_id == "retry-user-id"
        assert mock_auth_provider.create_user.await_count == 2

    async def test_register_re_raises_user_exists_after_conflict(self, mock_auth_provider, test_user_data):
        """Тест конфликта, после которого пользователь уже найден."""
        mock_auth_provider.get_user_by_username.side_effect = [None, {"id": "existing-id"}]
        mock_auth_provider.create_user.side_effect = AuthProviderConflictError()

        auth_service = AuthService(mock_auth_provider)

        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(**test_user_data)

    async def test_register_sends_event_when_producer_present(self, mock_auth_provider, test_user_data):
        """Тест отправки события при регистрации."""
        mock_auth_provider.get_user_by_username.return_value = None
        mock_auth_provider.create_user.return_value = "evt-user-id"
        mock_event_producer = AsyncMock()

        auth_service = AuthService(mock_auth_provider, mock_event_producer)
        await auth_service.register(**test_user_data)

        mock_event_producer.send_event.assert_awaited_once()

    async def test_register_ignores_event_producer_errors(self, mock_auth_provider, test_user_data):
        """Ошибки отправки события не должны ломать регистрацию."""
        mock_auth_provider.get_user_by_username.return_value = None
        mock_auth_provider.create_user.return_value = "evt-user-id"
        mock_event_producer = AsyncMock()
        mock_event_producer.send_event.side_effect = RuntimeError("kafka down")

        auth_service = AuthService(mock_auth_provider, mock_event_producer)
        user_id = await auth_service.register(**test_user_data)

        assert user_id == "evt-user-id"
        mock_event_producer.send_event.assert_awaited_once()

class TestAuthServiceLogin:
    """Тесты логина"""
    
    async def test_login_success(self, mock_auth_provider, test_login_data):
        """Тест успешного логина"""
        mock_auth_provider.login_with_username.return_value = {
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "expires_in": 300
        }
        mock_auth_provider.get_user_by_username.return_value = {"id": "user-123"}
        
        auth_service = AuthService(mock_auth_provider)
        result = await auth_service.login(**test_login_data)
        
        assert result["access_token"] == "test-token"
        assert result["user_id"] == "user-123"

    async def test_login_extracts_user_id_from_access_token(self, mock_auth_provider, test_login_data):
        """Если user не найден, user_id берется из access token"""
        payload = {"sub": "user-from-token"}
        raw = json.dumps(payload).encode("utf-8")
        token_payload = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

        mock_auth_provider.login_with_username.return_value = {
            "access_token": f"aaa.{token_payload}.bbb",
            "refresh_token": "test-refresh",
            "expires_in": 300,
        }
        mock_auth_provider.get_user_by_username.return_value = None

        auth_service = AuthService(mock_auth_provider)
        result = await auth_service.login(**test_login_data)

        assert result["user_id"] == "user-from-token"

    async def test_login_returns_none_if_token_payload_invalid(self, mock_auth_provider, test_login_data):
        """При битом токене user_id выставляется в None"""
        mock_auth_provider.login_with_username.return_value = {
            "access_token": "not.a.jwt",
            "refresh_token": "test-refresh",
            "expires_in": 300,
        }
        mock_auth_provider.get_user_by_username.return_value = None

        auth_service = AuthService(mock_auth_provider)
        result = await auth_service.login(**test_login_data)

        assert result["user_id"] is None


class TestAuthServicePasswordRecovery:
    """Тесты восстановления пароля"""

    async def test_forgot_password_sends_email_for_existing_user(self, mock_auth_provider):
        mock_auth_provider.get_user_by_username.return_value = {"id": "u-1"}
        auth_service = AuthService(mock_auth_provider)

        await auth_service.forgot_password("test@example.com")

        mock_auth_provider.send_reset_password_email.assert_awaited_once_with("u-1")

    async def test_forgot_password_does_not_send_for_unknown_user(self, mock_auth_provider):
        mock_auth_provider.get_user_by_username.return_value = None
        auth_service = AuthService(mock_auth_provider)

        await auth_service.forgot_password("missing@example.com")

        mock_auth_provider.send_reset_password_email.assert_not_awaited()


class TestAuthServiceWrappers:
    """Тесты passthrough-методов сервиса."""

    async def test_refresh_calls_provider(self, mock_auth_provider):
        mock_auth_provider.refresh_token.return_value = {"access_token": "new-token"}
        auth_service = AuthService(mock_auth_provider)

        result = await auth_service.refresh("refresh-token")

        assert result["access_token"] == "new-token"
        mock_auth_provider.refresh_token.assert_awaited_once_with("refresh-token")

    async def test_logout_calls_provider(self, mock_auth_provider):
        auth_service = AuthService(mock_auth_provider)

        await auth_service.logout("refresh-token")

        mock_auth_provider.logout.assert_awaited_once_with("refresh-token")

    async def test_logout_all_sessions_calls_provider(self, mock_auth_provider):
        auth_service = AuthService(mock_auth_provider)

        await auth_service.logout_all_sessions("user-id")

        mock_auth_provider.logout_all_sessions.assert_awaited_once_with("user-id")

    async def test_health_check_calls_provider(self, mock_auth_provider):
        mock_auth_provider.health_check.return_value = True
        auth_service = AuthService(mock_auth_provider)

        result = await auth_service.health_check()

        assert result is True
        mock_auth_provider.health_check.assert_awaited_once()

    async def test_reset_password_calls_provider(self, mock_auth_provider):
        auth_service = AuthService(mock_auth_provider)

        await auth_service.reset_password("action-token", "NewPass123!")

        mock_auth_provider.reset_password_with_action_token.assert_awaited_once_with(
            "action-token", "NewPass123!"
        )

    async def test_verify_email_calls_provider(self, mock_auth_provider):
        auth_service = AuthService(mock_auth_provider)

        await auth_service.verify_email("verify-token")

        mock_auth_provider.verify_email.assert_awaited_once_with("verify-token")