"""Unit тесты для AuthService"""
import pytest
from unittest.mock import AsyncMock, patch
from src.service.auth_service import AuthService, UserAlreadyExistsError
from src.service.abstractions_service import AuthProviderConflictError

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