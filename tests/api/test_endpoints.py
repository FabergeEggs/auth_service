import pytest
from httpx import HTTPStatusError, Response
from unittest.mock import AsyncMock, patch
from src.errors import InvalidTokenError, UserAlreadyExistsError

pytestmark = pytest.mark.asyncio

class TestHealthEndpoint:
    """Тесты health check"""
    
    async def test_health_check_healthy(self, client):
        """Тест успешного health check"""
        with patch('src.main.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.health_check = AsyncMock(return_value=True)
            mock_get_auth.return_value = mock_auth
            
            response = await client.get("/health")
            
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    async def test_health_check_unhealthy(self, client):
        """Тест неуспешного health check"""
        with patch('src.main.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.health_check = AsyncMock(return_value=False)
            mock_get_auth.return_value = mock_auth
            
            response = await client.get("/health")
            
            assert response.status_code == 503
            assert response.json()["status"] == "unhealthy"

class TestRegisterEndpoint:
    """Тесты эндпоинта регистрации"""
    
    async def test_register_success(self, client, test_user_data):
        """Тест успешной регистрации"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.register = AsyncMock(return_value="new-user-id")
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/register", json=test_user_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "new-user-id"
            assert data["message"] == "User registered successfully"
    
    async def test_register_user_exists(self, client, test_user_data):
        """Тест регистрации существующего пользователя"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.register = AsyncMock(side_effect=UserAlreadyExistsError("User exists"))
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/register", json=test_user_data)
            
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"].lower()
    
    async def test_register_invalid_data(self, client):
        """Тест регистрации с невалидными данными"""
        invalid_data = {
            "email": "invalid-email",
            "password": "123",
            "first_name": ""
        }
        
        response = await client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

class TestLoginEndpoint:
    """Тесты эндпоинта логина"""
    
    async def test_login_success(self, client, test_login_data):
        """Тест успешного логина"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.login = AsyncMock(return_value={
                "access_token": "test-token",
                "refresh_token": "test-refresh",
                "expires_in": 300,
                "refresh_expires_in": 2592000,
                "token_type": "bearer",
                "user_id": "user-123"
            })
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/login", json=test_login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test-token"
            assert data["user_id"] == "user-123"
            assert "refresh_token" in response.cookies
    
    async def test_login_invalid_credentials(self, client, test_login_data):
        """Тест неверных учетных данных"""
        
        
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.login = AsyncMock(side_effect=HTTPStatusError(
                "Invalid credentials",
                request=AsyncMock(),
                response=Response(401)
            ))
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/login", json=test_login_data)
            
            assert response.status_code == 401

class TestPasswordResetEndpoints:
    """Тесты эндпоинтов сброса пароля"""
    
    async def test_forgot_password_success(self, client):
        """Тест запроса на сброс пароля"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.forgot_password = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/forgot-password", json={
                "email": "test@example.com"
            })
            
            assert response.status_code == 200
            assert "message" in response.json()
    
    async def test_reset_password_success(self, client):
        """Тест сброса пароля"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.reset_password = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/reset-password", json={
                "key": "valid-token",
                "new_password": "NewTest123!@#",
                "confirm_password": "NewTest123!@#"
            })
            
            assert response.status_code == 200
            assert "successfully" in response.json()["message"].lower()
    
    async def test_reset_password_invalid_token(self, client):
        """Тест сброса пароля с невалидным токеном"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.reset_password = AsyncMock(side_effect=InvalidTokenError("Invalid token"))
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/reset-password", json={
                "key": "invalid-token",
                "new_password": "NewTest123!@#",
                "confirm_password": "NewTest123!@#"
            })
            
            assert response.status_code == 400

class TestEmailVerificationEndpoints:
    """Тесты эндпоинтов верификации email"""
    
    async def test_verify_email_success(self, client):
        """Тест верификации email"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.verify_email = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            response = await client.post("/api/v1/auth/verify-email", json={
                "key": "valid-verification-token"
            })
            
            assert response.status_code == 200
            assert "verified" in response.json()["message"].lower()
    
    async def test_verify_email_invalid_token(self, client):
        """Тест верификации email с невалидным токеном"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.verify_email = AsyncMock(side_effect=InvalidTokenError("Invalid token"))
            mock_get_auth.return_value = mock_auth

            response = await client.post("/api/v1/auth/verify-email", json={
                "key": "invalid-verification-token"
            })

            assert response.status_code == 400

class TestLogoutEndpoints:
    """Тесты эндпоинтов выхода"""
    
    async def test_logout_success(self, client):
        """Тест успешного выхода"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.logout = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            # Устанавливаем cookie с refresh токеном
            client.cookies.set("refresh_token", "test-refresh-token")
            
            response = await client.post("/api/v1/auth/logout")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            # Проверяем что cookie удален
            assert 'refresh_token' not in response.cookies
    
    async def test_logout_all_success(self, authenticated_client):
        """Тест выхода со всех устройств"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.logout_all_sessions = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            response = await authenticated_client.post("/api/v1/auth/logout-all")
            
            assert response.status_code == 200
            assert "terminated" in response.json()["message"].lower()

class TestRefreshTokenEndpoint:
    """Тесты обновления токена"""
    
    async def test_refresh_success(self, client):
        """Тест успешного обновления токена"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.refresh = AsyncMock(return_value={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 300,
                "refresh_expires_in": 2592000
            })
            mock_get_auth.return_value = mock_auth
            
            client.cookies.set("refresh_token", "valid-refresh-token")
            
            response = await client.post("/api/v1/auth/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new-access-token"
            assert "refresh_token" in response.cookies
    
    async def test_refresh_no_token(self, client):
        """Тест обновления без refresh токена"""
        response = await client.post("/api/v1/auth/refresh")
        
        assert response.status_code == 401