import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.adapters.keycloak_adapter import KeycloakAdapter, TokenVerifier
from src.api.handlers import create_app as create_fastapi_app
from src.service.auth_service import AuthService


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    keycloak_base_url: str = "http://localhost:8081"
    keycloak_realm: str = "myrealm"
    keycloak_client_id: str = "auth-service"
    keycloak_client_secret: str | None = None
    # Должен совпадать с полем iss в JWT. У Keycloak в Docker порт снаружи 8081,
    # но в токене часто iss с внутренним 8080 — см. .env KEYCLOAK_ISSUER.
    keycloak_issuer: str = "http://localhost:8080/realms/myrealm"
    keycloak_audience: str = "auth-service"

    @property
    def token_url(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/token"
        )

    @property
    def logout_url(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/logout"
        )

    @property
    def jwks_url(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/certs"
        )

    @property
    def admin_users_url(self) -> str:
        return f"{self.keycloak_base_url}/admin/realms/{self.keycloak_realm}/users"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app():
    _configure_logging()
    settings = Settings()

    keycloak_adapter = KeycloakAdapter(
        token_url=settings.token_url,
        logout_url=settings.logout_url,
        admin_users_url=settings.admin_users_url,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
    )
    token_verifier = TokenVerifier(
        jwks_url=settings.jwks_url,
        issuer=settings.keycloak_issuer,
        audience=settings.keycloak_audience,
    )
    auth_service = AuthService(auth_provider=keycloak_adapter)

    return create_fastapi_app(auth_service=auth_service, token_verifier=token_verifier)


app = create_app()
