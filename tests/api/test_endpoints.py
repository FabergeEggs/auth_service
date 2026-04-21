import pytest
from httpx import HTTPStatusError, Response
from unittest.mock import AsyncMock, MagicMock, patch
from src.errors import InvalidTokenError, KeycloakUnavailableError, UserAlreadyExistsError, KeycloakUnavailableError
from main import app
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
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

class TestMeEndpoint:
    """Тесты для эндпоинта /auth/me"""
    
    @pytest.mark.asyncio
    async def test_get_me_success(self, authenticated_client, mock_token_claims):
        """Тест успешного получения данных пользователя"""
        # Мокаем возврат данных от auth_service
        app.state.auth_service.me_payload = MagicMock(return_value={
            "sub": mock_token_claims["sub"],
            "email": mock_token_claims["email"],
            "preferred_username": mock_token_claims["preferred_username"],
            "name": mock_token_claims["name"],
            "given_name": mock_token_claims["given_name"],
            "family_name": mock_token_claims["family_name"],
            "phone": "+1234567890",
            "about": "Test about me",
            "realm_roles": ["user"],
            "client_roles": {"auth-service": ["user"]},
            "raw_claims": mock_token_claims
        })
        
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == mock_token_claims["sub"]
        assert data["email"] == mock_token_claims["email"]
        assert data["preferred_username"] == mock_token_claims["preferred_username"]
        assert "realm_roles" in data
        assert "client_roles" in data
    
    async def test_get_me_unauthorized(self, client):
        """Тест запроса без токена"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]
    
    async def test_get_me_invalid_token(self, client):
        """Тест с невалидным токеном"""
        client.headers["Authorization"] = "Bearer invalid-token"
        app.state.token_verifier.verify = AsyncMock(side_effect=ValueError("Invalid token"))
        
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    async def test_get_me_expired_token(self, client):
        """Тест с истёкшим токеном"""
        client.headers["Authorization"] = "Bearer expired-token"
        app.state.token_verifier.verify = AsyncMock(side_effect=ValueError("Token expired"))
        
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]

    async def test_get_me_service_error(self, authenticated_client):
        """Тест ошибки сервиса"""
        app.state.auth_service.me_payload = MagicMock(side_effect=ValueError("Invalid claims"))
        
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Invalid authentication data" in response.json()["detail"]
    
    async def test_get_me_unexpected_error(self, authenticated_client):
        """Тест неожиданной ошибки"""
        app.state.auth_service.me_payload = MagicMock(side_effect=Exception("Unexpected error"))
        
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 500
        assert "Failed to get user information" in response.json()["detail"]
    
    async def test_get_me_minimal_response(self, authenticated_client):
        """Тест минимального ответа (только sub)"""
        app.state.auth_service.me_payload = MagicMock(return_value={
            "sub": "test-user-id",
            "email": None,
            "preferred_username": None,
            "name": None,
            "given_name": None,
            "family_name": None,
            "phone": None,
            "about": None,
            "realm_roles": [],
            "client_roles": {},
            "raw_claims": {"sub": "test-user-id"}
        })
        
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "test-user-id"
        assert data["email"] is None
        assert data["realm_roles"] == []
    
class TestRequestPasswordChangeEndpoint:
    """Тесты для эндпоинта /auth/request-password-change"""
    
    @pytest.mark.asyncio
    async def test_request_password_change_success(self, authenticated_client, mock_token_claims):
        """Тест успешного запроса на смену пароля"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.forgot_password = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            response = await authenticated_client.post("/api/v1/auth/request-password-change")
            
            assert response.status_code == 200
            data = response.json()
            assert "Password change link has been sent" in data["message"]
            mock_auth.forgot_password.assert_awaited_once_with(mock_token_claims["email"])
    
    @pytest.mark.asyncio
    async def test_request_password_change_unauthorized(self, client):
        """Тест запроса без токена"""
        response = await client.post("/api/v1/auth/request-password-change")
        
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_request_password_change_no_email_in_token(self, authenticated_client):
        """Тест с токеном без email"""
        app.state.token_verifier.verify = AsyncMock(return_value={"sub": "user-123"})  # нет email
        
        response = await authenticated_client.post("/api/v1/auth/request-password-change")
        
        assert response.status_code == 400
        assert "Email not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_request_password_change_service_error(self, authenticated_client):
        """Тест ошибки сервиса"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.forgot_password = AsyncMock(side_effect=KeycloakUnavailableError("Service down"))
            mock_get_auth.return_value = mock_auth
            
            response = await authenticated_client.post("/api/v1/auth/request-password-change")
            
            assert response.status_code == 503
    
    @pytest.mark.asyncio
    async def test_request_password_change_rate_limit(self, authenticated_client):
        """Тест rate limiting"""
        with patch('src.api.handlers.get_auth_service') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.forgot_password = AsyncMock()
            mock_get_auth.return_value = mock_auth
            
            # Делаем 4 запроса (лимит 3/minute)
            responses = []
            for _ in range(4):
                resp = await authenticated_client.post("/api/v1/auth/request-password-change")
                responses.append(resp.status_code)
            
            assert 200 in responses[:3]
            assert 429 in responses  # Rate limit exceeded