from abc import ABC, abstractmethod
from typing import Optional, Protocol, Any



class AuthProviderConflictError(Exception):
    """Пользователь уже существует в провайдере"""
    pass

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
    ) -> str:
        """Создать пользователя, вернуть user_id"""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        """Получить пользователя по email"""
        pass
    
    @abstractmethod
    async def login_with_email(self, email: str, password: str) -> dict[str, Any]:
        """Залогинить по email"""
        pass
    
    @abstractmethod
    async def login_with_username(self, username: str, password: str) -> dict:
        """Залогинить по username"""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict:
        """Обновить токен"""
        pass
    
    @abstractmethod
    async def logout(self, refresh_token: str) -> None:
        """Выход (отзыв refresh token)"""
        pass
    
    @abstractmethod
    async def logout_all_sessions(self, user_id: str) -> None:
        """Отозвать ВСЕ сессии пользователя"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Проверить доступность провайдера"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Закрыть соединения"""
        pass


