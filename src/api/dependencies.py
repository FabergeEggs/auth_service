from fastapi import Header, HTTPException

from src.core.settings import settings
from src.services.token_verifier import TokenVerifier

verifier = TokenVerifier(
    jwks_url=settings.jwks_url,
    issuer=settings.keycloak_issuer,
    audience=settings.keycloak_audience,
)


async def get_current_claims(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return await verifier.verify(token)
