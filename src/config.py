from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://158.160.90.90:3000",
    ]
    refresh_token_max_age: int = 2592000
    frontend_url: str = Field("http://158.160.90.90:3000", alias="FRONTEND_URL")

    # Keycloak
    keycloak_url: str = Field("http://keycloak:8080", alias="KEYCLOAK_BASE_URL")
    realm: str = Field("myrealm", alias="KEYCLOAK_REALM")
    client_id: str = Field("auth-service", alias="KEYCLOAK_CLIENT_ID")
    client_secret: Optional[str] = Field(None, alias="KEYCLOAK_CLIENT_SECRET")
    admin_username: str = Field("admin", alias="KEYCLOAK_ADMIN_USERNAME")
    admin_password: str = Field("admin", alias="KEYCLOAK_ADMIN_PASSWORD")
    admin_client_id: str = Field("admin-cli", alias="KEYCLOAK_ADMIN_CLIENT_ID")

    # Kafka
    redpanda_bootstrap_servers: str = Field(
        "redpanda:9092", alias="REDPANDA_BOOTSTRAP_SERVERS"
    )
    kafka_enabled: bool = Field(True, alias="KAFKA_ENABLED")

    # Database
    database_url: str = Field("", alias="DATABASE_URL")

    keycloak_public_url: str = Field(
        "http://localhost:3000", alias="KEYCLOAK_PUBLIC_URL"
    )
    token_audience: str = Field("account", alias="KEYCLOAK_TOKEN_AUDIENCE")

    @property
    def issuer(self) -> str:
        return f"{self.keycloak_public_url}/realms/{self.realm}"

    @property
    def audience(self) -> str:
        return self.token_audience

    @property
    def token_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

    @property
    def logout_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/logout"

    @property
    def admin_users_url(self) -> str:
        return f"{self.keycloak_url}/admin/realms/{self.realm}/users"

    @property
    def admin_token_url(self) -> str:
        return f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"

    @property
    def jwks_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"

    @property
    def secure_cookies(self) -> bool:
        return self.environment == "production"

    @property
    def cookie_domain(self) -> Optional[str]:
        return None


settings = Settings()  # type: ignore[call-arg]
