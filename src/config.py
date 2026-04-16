from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # ← важно! игнорировать лишние переменные
    )

    environment: str = "development"
    cors_origins: List[str] = ["http://localhost:3000"]

    # Добавляем алиасы для совместимости с текущим .env
    keycloak_url: str = Field("http://keycloak:8080", alias="KEYCLOAK_BASE_URL")
    realm: str = Field("myrealm", alias="KEYCLOAK_REALM")
    client_id: str = Field("myclient", alias="KEYCLOAK_CLIENT_ID")
    client_secret: Optional[str] = Field(None, alias="KEYCLOAK_CLIENT_SECRET")

    admin_username: str = Field(..., alias="KEYCLOAK_ADMIN_USERNAME")
    admin_password: str = Field(..., alias="KEYCLOAK_ADMIN_PASSWORD")
    admin_client_id: str = Field("admin-cli", alias="KEYCLOAK_ADMIN_CLIENT_ID")

    frontend_url: str = "http://localhost:3000"

    refresh_token_max_age: int = 2592000

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
    def issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}"

    @property
    def audience(self) -> str:
        return self.client_id

settings = Settings()