import logging
import base64
import json
from typing import Optional
from src.service.abstractions_service import AuthProviderInterface
from src.errors import AuthProviderConflictError, UserAlreadyExistsError

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, auth_provider: AuthProviderInterface, event_producer=None):
        self._auth_provider = auth_provider
        self._event_producer = event_producer

    async def register(self, email: str, password: str, first_name: str,
                       last_name: Optional[str] = None, phone: Optional[str] = None,
                       about: Optional[str] = None) -> str:
        if await self._auth_provider.get_user_by_username(email):
            raise UserAlreadyExistsError(f"User {email} already exists")

        try:
            user_id = await self._auth_provider.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name, phone=phone, about=about
            )
        except AuthProviderConflictError:
            existing = await self._auth_provider.get_user_by_username(email)
            if existing:
                raise UserAlreadyExistsError(f"User {email} already exists")
            user_id = await self._auth_provider.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name, phone=phone, about=about
            )
        
        logger.info("User registered", extra={"event": "register", "user_id": user_id})
        
        if self._event_producer:
            try:
                await self._event_producer.send_event("keycloak.user.registered", {
                    "user_id": user_id,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "about": about
                })
                logger.info(f"UserRegistered event sent for {user_id}")
            except Exception as e:
                logger.error(f"Failed to send UserRegistered event: {e}", exc_info=True)
        
        return user_id

    async def login(self, login: str, password: str) -> dict:

        tokens = await self._auth_provider.login_with_username(login, password)
        # Пытаемся получить пользователя по username
        user = await self._auth_provider.get_user_by_username(login)
        
        # Добавляем user_id в ответ
        if user:
            tokens["user_id"] = user.get("id")
        else:
            # Fallback: извлекаем из access_token
            try:
                payload = tokens["access_token"].split('.')[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload).decode('utf-8')
                claims = json.loads(decoded)
                tokens["user_id"] = claims.get("sub")
            except Exception as e:
                logger.warning(f"Failed to extract user_id from token: {e}")
                tokens["user_id"] = None
        
        return tokens

    async def refresh(self, refresh_token: str) -> dict:
        return await self._auth_provider.refresh_token(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        await self._auth_provider.logout(refresh_token)

    async def logout_all_sessions(self, user_id: str) -> None:
        await self._auth_provider.logout_all_sessions(user_id)

    async def health_check(self) -> bool:
        return await self._auth_provider.health_check()

    async def forgot_password(self, email: str) -> None:
        """
        Отправляет email со ссылкой для сброса пароля через Keycloak.
        """
        user = await self._auth_provider.get_user_by_username(email)
        if not user:
            # Не раскрываем существование пользователя
            logger.info("Forgot password requested for non-existent email", extra={"email": email})
            return

        await self._auth_provider.send_reset_password_email(user["id"])
        logger.info("Password reset email sent", extra={"user_id": user["id"]})

    async def reset_password(self, action_token: str, new_password: str) -> None:
        """
        Сбрасывает пароль, используя action token (параметр 'key' из письма).
        """
        await self._auth_provider.reset_password_with_action_token(action_token, new_password)
        logger.info("Password reset successful")

    async def verify_email(self, action_token: str) -> None:
        """Подтверждает email по action token"""
        await self._auth_provider.verify_email(action_token)
        logger.info("Email verified successfully")
    