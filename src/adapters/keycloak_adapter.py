import logging
import time
import asyncio
from typing import Optional, Dict, Any, cast
import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from src.service.abstractions_service import AuthProviderConflictError

logger = logging.getLogger(__name__)

class KeycloakUserAttributes:
    PHONE = "phone"
    ABOUT = "about"

class KeycloakUnavailableError(Exception):
    """Keycloak недоступен или ошибка аутентификации администратора"""
    pass

class KeycloakConflictError(AuthProviderConflictError):
    pass

class AuthServiceError(Exception):
    pass

class InvalidTokenError(AuthServiceError):
    pass

class UserNotFoundError(AuthServiceError):
    pass

class KeycloakError(AuthServiceError):
    pass

class KeycloakAdapter:
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    ADMIN_TOKEN_BUFFER = 60

    def __init__(self, token_url: str, logout_url: str, admin_users_url: str,
                 client_id: str, client_secret: Optional[str] = None,
                 admin_username: str = "admin", admin_password: str = "admin",
                 admin_client_id: str = "admin-cli",
                 admin_token_url: str = "http://keycloak:8080/realms/master/protocol/openid-connect/token",
                 realm: str = "myrealm", frontend_url: str = "http://localhost:3000"):
        self.token_url = token_url
        self.base_url = token_url.split("/realms")[0]
        self.frontend_url = frontend_url
        self.logout_url = logout_url
        self.admin_users_url = admin_users_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_client_id = admin_client_id
        self.admin_token_url = admin_token_url
        self.realm = realm
        self._admin_token: Optional[str] = None
        self._admin_token_expires_at: float = 0.0
        self._admin_token_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

    async def close(self):
        await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            base = self.token_url.split("/realms")[0]
            resp = await self._client.get(f"{base}/realms/{self.realm}")
            return resp.status_code < 500
        except Exception:
            return False

    async def _get_admin_token(self) -> str:
        if self._admin_token and time.time() < self._admin_token_expires_at:
            return cast(str, self._admin_token)
        async with self._admin_token_lock:
            if self._admin_token and time.time() < self._admin_token_expires_at:
                return cast(str, self._admin_token)
            data = {
                "client_id": self.admin_client_id,
                "username": self.admin_username,
                "password": self.admin_password,
                "grant_type": "password"
            }
            try:
                resp = await self._client.post(self.admin_token_url, data=data)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("Failed to get admin token: %s", e)
                raise KeycloakUnavailableError("Keycloak admin token unavailable") from e
            except httpx.RequestError as e:
                logger.error("Network error getting admin token: %s", e)
                raise KeycloakUnavailableError("Keycloak unreachable") from e
            
            token_data = resp.json()
            token = token_data["access_token"]
            self._admin_token = token
            expires = token_data.get("expires_in", 300)
            self._admin_token_expires_at = time.time() + expires - self.ADMIN_TOKEN_BUFFER
            return cast(str, self._admin_token)

    async def _retry_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = await self._client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                logger.warning("Network error on attempt %d/%d for %s %s: %s", 
                             attempt + 1, self.MAX_RETRIES, method, url, e)
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    raise
                last_exc = e
                logger.warning("HTTP %d on attempt %d/%d for %s %s", 
                             e.response.status_code, attempt + 1, self.MAX_RETRIES, method, url)
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (2 ** attempt))
        if last_exc is None:
            raise RuntimeError("Retry loop ended without exception")
        raise last_exc


    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по username"""
        token: str = await self._get_admin_token()
        resp = await self._retry_request(
            "GET", self.admin_users_url,
            headers={"Authorization": f"Bearer {token}"},
            params={"username": username, "exact": "true"}
        )
        users = resp.json()
        return cast(Optional[Dict[str, Any]], users[0]) if users else None

    async def create_user(self, username: str, email: str, password: str,
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      phone: Optional[str] = None, about: Optional[str] = None) -> str:
        token: str = await self._get_admin_token() 
        user_data = {
            "username": username,
            "email": email,
            "enabled": True,
            "emailVerified": False,
            "credentials": [{"type": "password", "value": password, "temporary": False}]
        }
        if first_name:
            user_data["firstName"] = first_name
        if last_name:
            user_data["lastName"] = last_name
        
        attributes = {}
        if phone:
            attributes[KeycloakUserAttributes.PHONE] = [phone]
        if about:
            attributes[KeycloakUserAttributes.ABOUT] = [about]
        if attributes:
            user_data["attributes"] = attributes
        
        try:
            resp = await self._retry_request(
                "POST", self.admin_users_url,
                headers={"Authorization": f"Bearer {token}"},
                json=user_data
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise KeycloakConflictError("User already exists") from e
            raise
        
        location = resp.headers.get("Location")
        if location:
            user_id = location.split("/")[-1]
            await self.send_verification_email(user_id)
            return user_id
        raise Exception("No user id returned")
    
    async def send_verification_email(self, user_id: str) -> None:
        """Отправить письмо для верификации email"""
        token = await self._get_admin_token()
        try:
            await self._retry_request(
                "PUT",
                f"{self.admin_users_url}/{user_id}/execute-actions-email",
                headers={"Authorization": f"Bearer {token}"},
                json=["VERIFY_EMAIL"]
            )
            logger.info(f"Verification email sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            raise

    async def verify_email(self, action_token: str) -> None:
        """
        Подтверждает email по action token.
        Использует публичный endpoint Keycloak для верификации.
        """
        # Публичный endpoint Keycloak для обработки action tokens
        verify_url = f"{self.base_url}/realms/{self.realm}/login-actions/action-token"
        
        # Данные для верификации
        data = {
            "token": action_token,
            "client_id": self.client_id
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            # Keycloak сам валидирует токен и подтверждает email
            resp = await self._client.post(verify_url, data=data)
            
            if resp.status_code == 200:
                logger.info("Email verified successfully")
                return
            elif resp.status_code == 400:
                # Анализируем ошибку
                error_text = resp.text.lower()
                if "expired" in error_text:
                    raise InvalidTokenError("Verification token has expired")
                elif "invalid" in error_text:
                    raise InvalidTokenError("Invalid verification token")
                else:
                    raise InvalidTokenError(f"Verification failed: {resp.text}")
            else:
                resp.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Email verification failed: {e}")
            if e.response.status_code == 400:
                raise InvalidTokenError("Invalid or expired verification token")
            raise KeycloakError(f"Verification failed: {e}")

    async def login_with_username(self, username: str, password: str) -> dict:
        return await self._login_with_username(username, password)

    async def _login_with_username(self, username: str, password: str) -> dict:
        data = {
            "client_id": self.client_id,
            "username": username,
            "password": password,
            "grant_type": "password"
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        resp = await self._retry_request("POST", self.token_url, data=data)
        return resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        resp = await self._retry_request("POST", self.token_url, data=data)
        return resp.json()

    
    async def send_reset_password_email(self, user_id: str) -> None:
        """
        Вызывает Keycloak API для отправки письма со ссылкой сброса пароля.
        """
        token: str = await self._get_admin_token()
        try:
            await self._retry_request(
                "PUT",
                f"{self.admin_users_url}/{user_id}/execute-actions-email",
                headers={"Authorization": f"Bearer {token}"},
                params={"redirect_uri": f"{self.frontend_url}/reset-password"},
                json=["UPDATE_PASSWORD"],
            )
            logger.info(f"Password reset email sent to user {user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("User %s not found when sending reset email", user_id)
                raise UserNotFoundError(f"User {user_id} not found")
            raise

    async def reset_password_with_action_token(self, action_token: str, new_password: str) -> None:
        """
        Сброс пароля через action token.
        Использует публичный endpoint Keycloak для сброса пароля.
        """
        # Endpoint для сброса пароля через action token
        reset_url = f"{self.base_url}/realms/{self.realm}/login-actions/reset-credentials"
        
        data = {
            "token": action_token,
            "password-new": new_password,
            "password-confirm": new_password,
            "client_id": self.client_id
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            resp = await self._client.post(reset_url, data=data)
            
            if resp.status_code == 200:
                logger.info("Password reset successful")
                return
            elif resp.status_code == 400:
                error_text = resp.text.lower()
                if "expired" in error_text:
                    raise InvalidTokenError("Reset token has expired")
                elif "invalid" in error_text:
                    raise InvalidTokenError("Invalid reset token")
                elif "password" in error_text:
                    raise ValueError(f"Invalid password: {resp.text}")
                else:
                    raise InvalidTokenError(f"Password reset failed: {resp.text}")
            else:
                resp.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Password reset failed: {e}")
            if e.response.status_code == 400:
                raise InvalidTokenError("Invalid or expired reset token")
            raise KeycloakError(f"Password reset failed: {e}")

    async def logout(self, refresh_token: str) -> None:
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        await self._retry_request("POST", self.logout_url, data=data)

    async def logout_all_sessions(self, user_id: str) -> None:
        token: str = await self._get_admin_token()
        try:
            await self._retry_request(
                "DELETE", f"{self.admin_users_url}/{user_id}/sessions",
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info(f"All sessions terminated for user {user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("User %s not found when terminating sessions", user_id)
            else:
                raise
        except Exception as e:
            logger.error("Failed to logout all sessions for user %s: %s", user_id, e)
            raise

    
    


class TokenVerifier:
    def __init__(self, jwks_url: str, issuer: str, audience: str):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: float = 0.0
        self._cache_ttl: int = 600

    async def close(self):
        await self._client.aclose()

    async def _get_signing_key(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            if not kid:
                logger.error("No kid in token header")
                return None
            
            # Проверяем кеш
            now = time.time()
            if self._jwks_cache is not None and (now - self._jwks_cache_time) < self._cache_ttl:
                keys = self._jwks_cache.get("keys", [])
            else:
                resp = await self._client.get(self.jwks_url)
                resp.raise_for_status()
                self._jwks_cache = resp.json()
                self._jwks_cache_time = now
                keys = self._jwks_cache.get("keys", []) if self._jwks_cache else []
            
            for k in keys:
                if k.get("kid") == kid:
                    return k
            logger.error("No key with kid=%s found in JWKS", kid)
        except Exception as e:
            logger.error("Failed to fetch JWKS: %s", e)
        return None

    async def verify(self, token: str) -> Dict[str, Any]:
        key = await self._get_signing_key(token)
        if not key:
            raise ValueError("No signing key available")
        try:
            return cast(Dict[str, Any], jwt.decode(
                token, key, algorithms=["RS256"],
                issuer=self.issuer, audience=self.audience,
                options={"verify_signature": True, "verify_exp": True}
            ))
        except ExpiredSignatureError:
            raise ValueError("Token expired")
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")