import httpx
from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, status


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

    def invalidate_cache(self) -> None:
        self._jwks_cache = None

    async def verify(self, token: str) -> dict:
        try:
            jwks = await self._get_jwks()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            key = next(
                (k for k in jwks.get("keys", []) if k.get("kid") == kid),
                None,
            )
            if not key:
                self.invalidate_cache()
                jwks = await self._get_jwks()
                key = next(
                    (k for k in jwks.get("keys", []) if k.get("kid") == kid),
                    None,
                )
            if not key:
                raise HTTPException(status_code=401, detail="Signing key not found")

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
