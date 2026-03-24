from typing import Protocol


class AuthProvider(Protocol):
    async def register(self, username: str, email: str, password: str) -> str: ...

    async def password_login(self, username: str, password: str) -> dict: ...

    async def refresh(self, refresh_token: str) -> dict: ...

    async def logout(self, refresh_token: str) -> None: ...


class AuthService:
    def __init__(self, auth_provider: AuthProvider):
        self.auth_provider = auth_provider

    async def register(self, username: str, email: str, password: str) -> str:
        return await self.auth_provider.register(
            username=username,
            email=email,
            password=password,
        )

    async def login(self, email: str, password: str) -> dict:
        return await self.auth_provider.password_login(
            username=email,
            password=password,
        )

    async def refresh(self, refresh_token: str) -> dict:
        return await self.auth_provider.refresh(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        await self.auth_provider.logout(refresh_token)

    @staticmethod
    def me_payload(claims: dict) -> dict:
        return {
            "sub": claims.get("sub", ""),
            "email": claims.get("email"),
            "preferred_username": claims.get("preferred_username"),
            "realm_roles": claims.get("realm_access", {}).get("roles", []),
            "client_roles": {
                client: data.get("roles", [])
                for client, data in claims.get("resource_access", {}).items()
            },
            "raw_claims": claims,
        }
