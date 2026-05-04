# tests/integration/test_keycloak_real.py
import pytest
from src.adapters.keycloak_adapter import KeycloakAdapter
from src.errors import KeycloakConflictError, UserNotFoundError


@pytest.mark.integration
@pytest.mark.asyncio
class TestKeycloakRealIntegration:
    """Интеграционные тесты с реальным Keycloak"""

    async def test_health_check_real(self, keycloak_adapter: KeycloakAdapter):
        """Health check возвращает true на HTTP 200."""
        is_healthy = await keycloak_adapter.health_check()
        assert is_healthy is True

    async def test_create_and_get_user_real(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Создание пользователя и получение по username."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            assert user_id is not None
            assert len(user_id) > 0

            # Получаем пользователя по username
            user = await keycloak_adapter.get_user_by_username(
                test_user_data["username"]
            )
            assert user is not None
            assert user["username"] == test_user_data["username"]
            assert user["email"] == test_user_data["email"]
            assert user["firstName"] == test_user_data["first_name"]
            assert user["lastName"] == test_user_data["last_name"]
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_create_duplicate_user_fails(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Создание дубликата пользователя вызывает ошибку конфликта."""
        # Создаём пользователя первый раз
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Пытаемся создать второго такого же
            with pytest.raises(KeycloakConflictError):
                await keycloak_adapter.create_user(**test_user_data)
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_login_with_username_success(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Успешный логин с username/password."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Логинимся
            result = await keycloak_adapter.login_with_username(
                username=test_user_data["username"], password=test_user_data["password"]
            )

            assert "access_token" in result
            assert "refresh_token" in result
            assert result["token_type"] == "Bearer"
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_login_with_email_success(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Успешный логин с email/password."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Логинимся с email
            result = await keycloak_adapter.login_with_username(
                username=test_user_data["email"], password=test_user_data["password"]
            )

            assert "access_token" in result
            assert "refresh_token" in result
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_login_wrong_password_fails(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Логин с неправильным паролем вызывает ошибку."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Логинимся с неправильным паролем
            with pytest.raises(Exception):  # Keycloak вернёт 401
                await keycloak_adapter.login_with_username(
                    username=test_user_data["username"], password="WrongPassword123!"
                )
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_get_nonexistent_user(self, keycloak_adapter: KeycloakAdapter):
        """Получение несуществующего пользователя возвращает None."""
        user = await keycloak_adapter.get_user_by_username("nonexistent_user_12345")
        assert user is None

    async def test_send_reset_password_email(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Отправка письма для сброса пароля."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Отправляем письмо
            await keycloak_adapter.send_reset_password_email(user_id)
            # Если не упало - ок
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)

    async def test_send_reset_password_email_nonexistent_user(
        self, keycloak_adapter: KeycloakAdapter
    ):
        """Отправка письма несуществующему пользователю вызывает ошибку."""
        with pytest.raises(UserNotFoundError):
            await keycloak_adapter.send_reset_password_email("nonexistent-user-id")

    async def test_logout_all_sessions(
        self, keycloak_adapter: KeycloakAdapter, test_user_data: dict
    ):
        """Завершение всех сессий пользователя."""
        # Создаём пользователя
        user_id = await keycloak_adapter.create_user(**test_user_data)

        try:
            # Логинимся чтобы создать сессию
            await keycloak_adapter.login_with_username(
                username=test_user_data["username"], password=test_user_data["password"]
            )

            # Завершаем все сессии
            await keycloak_adapter.logout_all_sessions(user_id)
            # Если не упало - ок
        finally:
            # Очистка
            await keycloak_adapter.delete_user(user_id)
