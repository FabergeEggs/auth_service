from abc import abstractmethod
from typing import Optional, Protocol, Any


class AuthProviderInterface(Protocol):
    """Интерфейс для провайдера аутентификации"""

    @abstractmethod
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        about: Optional[str] = None,
    ) -> str: ...

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    async def login_with_username(self, username: str, password: str) -> dict: ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict: ...

    @abstractmethod
    async def send_reset_password_email(self, user_id: str) -> None: ...

    @abstractmethod
    async def reset_password_with_action_token(
        self, action_token: str, new_password: str
    ) -> None: ...

    @abstractmethod
    async def send_verification_email(self, user_id: str) -> None: ...

    @abstractmethod
    async def verify_email(self, action_token: str) -> None: ...

    @abstractmethod
    async def logout(self, refresh_token: str) -> None: ...

    @abstractmethod
    async def logout_all_sessions(self, user_id: str) -> None: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def close(self) -> None: ...
