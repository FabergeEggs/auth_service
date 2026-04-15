import logging
from typing import Optional, Dict, Any
from src.service.abstractions_service import AuthProviderInterface
from src.service.abstractions_service import AuthProviderConflictError

logger = logging.getLogger(__name__)

class UserAlreadyExistsError(Exception):
    pass

class AuthService:
    def __init__(self, auth_provider: AuthProviderInterface):
        self._auth_provider = auth_provider

    async def register(self, email: str, password: str, first_name: str,
                       last_name: Optional[str] = None, phone: Optional[str] = None,
                       about: Optional[str] = None) -> str:
        if await self._auth_provider.get_user_by_email(email):
            raise UserAlreadyExistsError(f"User {email} already exists")

        try:
            user_id = await self._auth_provider.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name, phone=phone, about=about
            )
        except AuthProviderConflictError:
            existing = await self._auth_provider.get_user_by_email(email)
            if existing:
                raise UserAlreadyExistsError(f"User {email} already exists")
            user_id = await self._auth_provider.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name, phone=phone, about=about
            )
        logger.info("User registered", extra={"event": "register", "user_id": user_id})
        return user_id

    async def login(self, login: str, password: str) -> dict:
        if "@" in login:
            return await self._auth_provider.login_with_email(login, password)
        return await self._auth_provider.login_with_username(login, password)

    async def refresh(self, refresh_token: str) -> dict:
        return await self._auth_provider.refresh_token(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        await self._auth_provider.logout(refresh_token)

    async def logout_all_sessions(self, user_id: str) -> None:
        await self._auth_provider.logout_all_sessions(user_id)

    async def health_check(self) -> bool:
        return await self._auth_provider.health_check()

    def _get_attr(self, claims: dict, attr: str) -> Optional[str]:
        val = claims.get("attributes", {}).get(attr)
        return val[0] if isinstance(val, list) and val else None

    def me_payload(self, claims: dict) -> Dict[str, Any]:
        resource_access = claims.get("resource_access", {})
        client_roles = {
            cid: acc.get("roles", [])
            for cid, acc in resource_access.items()
            if acc.get("roles")
        }
        return {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "preferred_username": claims.get("preferred_username"),
            "name": claims.get("name"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "phone": self._get_attr(claims, "phone"),
            "about": self._get_attr(claims, "about"),
            "realm_roles": claims.get("realm_access", {}).get("roles", []),
            "client_roles": client_roles,
            "raw_claims": claims,
        }
