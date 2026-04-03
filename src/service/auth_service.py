from typing import Optional
import logging

from src.adapters.keycloak_adapter import KeycloakAdapter

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, auth_provider: KeycloakAdapter):
        self.auth_provider = auth_provider

    async def register(
    self,
    email: str,
    password: str,
    first_name: str,          
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    about: Optional[str] = None ) -> str:
        user_id = await self.auth_provider.create_user(
            username=email,           # email используется как username
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            about=about )
        return user_id

    async def login(self, login: str, password: str) -> dict:
        """Логин по email или username"""
        if "@" in login:
            return await self.auth_provider.login_with_email(login, password)
        else:
            return await self.auth_provider.login_with_username(login, password)

    async def refresh(self, refresh_token: str) -> dict:
        """Обновление токена"""
        return await self.auth_provider.refresh_token(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        """Выход пользователя"""
        await self.auth_provider.logout(refresh_token)

    def me_payload(self, claims: dict) -> dict:
        """Формирование payload для /me"""
        return {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "preferred_username": claims.get("preferred_username"),
            "name": claims.get("name"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "phone": claims.get("attributes", {}).get("phone", [None])[0] if claims.get("attributes") else None,
            "about": claims.get("attributes", {}).get("about", [None])[0] if claims.get("attributes") else None,
            "realm_roles": claims.get("realm_access", {}).get("roles", []),
            "client_roles": claims.get("resource_access", {}),
            "raw_claims": claims,
        }