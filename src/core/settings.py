from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Auth Service"

    keycloak_base_url: str = "http://localhost:8081"
    keycloak_realm: str = "myrealm"
    keycloak_client_id: str = "auth-service"
    keycloak_client_secret: str | None = None

    keycloak_issuer: str = "http://localhost:8081/realms/myrealm"
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
        return (
            f"{self.keycloak_base_url}/admin/realms/{self.keycloak_realm}/users"
        )


settings = Settings()
