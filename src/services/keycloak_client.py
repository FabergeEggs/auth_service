import httpx


class KeycloakClient:
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
        """Get service-account token for Admin REST API calls."""
        data = {**self._client_creds(), "grant_type": "client_credentials"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def register(
        self,
        username: str,
        email: str,
        password: str,
    ) -> str:
        """Create user via Keycloak Admin REST API. Returns created user id."""
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
            user_id = location.rsplit("/", maxsplit=1)[-1] if location else ""
            return user_id

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


class KeycloakConflictError(Exception):
    pass
