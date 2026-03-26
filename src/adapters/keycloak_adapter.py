import logging
from typing import Optional
import base64
import json

import httpx

logger = logging.getLogger(__name__)


class KeycloakAdapter:
    """Адаптер для взаимодействия с Keycloak API"""

    def __init__(
        self,
        token_url: str,
        logout_url: str,
        admin_users_url: str,
        client_id: str,
        client_secret: Optional[str] = None,
    ):
        self.token_url = token_url
        self.logout_url = logout_url
        self.admin_users_url = admin_users_url
        self.client_id = client_id
        self.client_secret = client_secret

    async def _get_admin_token(self) -> str:
        """Получение административного токена"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": "admin-cli",
                "username": "admin",
                "password": "admin",
                "grant_type": "password",
            }
            response = await client.post(
                "http://keycloak:8080/realms/master/protocol/openid-connect/token",
                data=data,
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        about: Optional[str] = None,
    ) -> str:
        """Создание пользователя в Keycloak"""
        admin_token = await self._get_admin_token()

        user_data = {
            "username": username,
            "email": email,
            "enabled": True,
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": False,
                }
            ],
        }

        # Добавляем имя и фамилию
        if first_name:
            user_data["firstName"] = first_name
        if last_name:
            user_data["lastName"] = last_name

        # Добавляем атрибуты (телефон, о себе)
        attributes = {}
        if phone:
            attributes["phone"] = [phone]
        if about:
            attributes["about"] = [about]

        if attributes:
            user_data["attributes"] = attributes

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.admin_users_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json",
                },
                json=user_data,
            )

            if response.status_code == 409:
                raise KeycloakConflictError("User already exists")
            response.raise_for_status()

            # Получаем ID созданного пользователя из Location header
            location = response.headers.get("Location")
            if location:
                user_id = location.split("/")[-1]
                return user_id

            raise Exception("Failed to get user id from response")

    async def login_with_email(self, email: str, password: str) -> dict:
        """Логин по email"""
        return await self._login_with_username(email, password)

    async def login_with_username(self, username: str, password: str) -> dict:
        """Логин по username"""
        return await self._login_with_username(username, password)

    async def _login_with_username(self, username: str, password: str) -> dict:
        """Внутренний метод логина"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "username": username,
                "password": password,
                "grant_type": "password",
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Обновление токена"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()

    async def logout(self, refresh_token: str) -> None:
        """Выход пользователя"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "refresh_token": refresh_token,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await client.post(self.logout_url, data=data)
            response.raise_for_status()

    async def get_user_info(self, user_id: str) -> dict:
        """Получение информации о пользователе по ID"""
        admin_token = await self._get_admin_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.admin_users_url}/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            response.raise_for_status()
            return response.json()


class KeycloakConflictError(Exception):
    """Исключение при конфликте (пользователь уже существует)"""
    pass


class TokenVerifier:
    """Верификатор JWT токенов"""

    def __init__(self, jwks_url: str, issuer: str, audience: str):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience

    async def verify(self, token: str) -> dict:
        """Верификация токена"""
        # В реальной реализации здесь должна быть проверка подписи
        # с использованием JWKS и библиотеки python-jose
        # Для упрощения возвращаем декодированные claims
        
        # Простое декодирование без проверки подписи
        # В продакшене используйте python-jose для полноценной верификации
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            
            # Декодируем payload (вторую часть)
            payload = parts[1]
            # Добавляем padding если нужно
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            
            # Проверяем issuer
            if claims.get("iss") != self.issuer:
                raise ValueError(f"Invalid issuer: {claims.get('iss')}")
            
            # Проверяем audience
            aud = claims.get("aud")
            if aud and aud != self.audience:
                raise ValueError(f"Invalid audience: {aud}")
            
            return claims
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise ValueError("Invalid token")