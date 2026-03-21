import httpx
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTError


class KeycloakConflictError(Exception):
    pass


class KeycloakAdapter:
    def __init__(
        self,
        token_url: str,
        logout_url: str,
        admin_users_url: str,
        client_id: str,
        client_secret: str | None,
    ):
        self.token_url = token_url
        self.logout_url = logout_url
        self.admin_users_url = admin_users_url
        self.client_id = client_id
        self.client_secret = client_secret

    def _client_creds(self) -> dict[str, str]:
        creds: dict[str, str] = {"client_id": self.client_id}
        if self.client_secret:
            creds["client_secret"] = self.client_secret
        return creds

    async def _get_admin_token(self) -> str:
        data = {**self._client_creds(), "grant_type": "client_credentials"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def register(self, username: str, email: str, password: str) -> str:
        admin_token = await self._get_admin_token()
        user_payload = {
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

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                self.admin_users_url,
                json=user_payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            if resp.status_code == 409:
                raise KeycloakConflictError("User already exists")
            resp.raise_for_status()

            location = resp.headers.get("Location", "")
            return location.rsplit("/", maxsplit=1)[-1] if location else ""

    async def password_login(self, username: str, password: str) -> dict:
        data = {
            **self._client_creds(),
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def refresh(self, refresh_token: str) -> dict:
        data = {
            **self._client_creds(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def logout(self, refresh_token: str) -> None:
        data = {**self._client_creds(), "refresh_token": refresh_token}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.logout_url, data=data)
            resp.raise_for_status()


class TokenVerifier:
    def __init__(self, jwks_url: str, issuer: str, audience: str):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self._jwks_cache: dict | None = None

    async def _get_jwks(self) -> dict:
        if self._jwks_cache is not None:
            return self._jwks_cache
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            self._jwks_cache = resp.json()
            return self._jwks_cache

    async def verify(self, token: str) -> dict:
        try:
            jwks = await self._get_jwks()
            kid = jwt.get_unverified_header(token).get("kid")
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                self._jwks_cache = None
                jwks = await self._get_jwks()
                key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                raise HTTPException(status_code=401, detail="Signing key not found")

            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
