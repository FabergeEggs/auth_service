import pytest
from pydantic import ValidationError
from src.api.dto import (
    RegisterRequestDTO,
    RegisterResponseDTO,
    LoginRequestDTO,
    TokenResponseDTO,
    ForgotPasswordRequestDTO,
    ResetPasswordRequestDTO,
    VerifyEmailRequestDTO,
    MeResponseDTO
)


class TestRegisterRequestDTO:
    """Тесты DTO регистрации"""
    
    def test_valid_registration_minimal(self):
        """Тест с минимальным набором полей"""
        dto = RegisterRequestDTO(
            email="test@example.com",
            password="SecurePass123!",
            first_name="Test"
        )
        assert dto.email == "test@example.com"
        assert dto.first_name == "Test"
        assert dto.last_name is None
        assert dto.phone is None
        assert dto.about is None
    
    def test_valid_registration_all_fields(self):
        """Тест со всеми полями"""
        dto = RegisterRequestDTO(
            email="full@example.com",
            password="SecurePass123!",
            first_name="Test",
            last_name="User",
            phone="+79001234567",
            about="Software Developer"
        )
        assert dto.email == "full@example.com"
        assert dto.first_name == "Test"
        assert dto.last_name == "User"
        assert dto.phone == "+79001234567"
        assert dto.about == "Software Developer"
    
    def test_invalid_email(self):
        """Тест невалидного email"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="invalid-email",
                password="SecurePass123!",
                first_name="Test"
            )
        assert "email" in str(exc.value)
    
    def test_weak_password(self):
        """Тест слабого пароля (меньше 6 символов)"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="123",
                first_name="Test"
            )
        assert "password" in str(exc.value)
    
    def test_empty_first_name(self):
        """Тест пустого имени"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name=""
            )
        assert "first_name" in str(exc.value)
    
    def test_too_long_first_name(self):
        """Тест слишком длинного имени"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name="A" * 51
            )
        assert "first_name" in str(exc.value)
    
    def test_too_long_last_name(self):
        """Тест слишком длинной фамилии"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name="Test",
                last_name="B" * 51
            )
        assert "last_name" in str(exc.value)
    
    def test_too_long_about(self):
        """Тест слишком длинного about"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name="Test",
                about="C" * 501
            )
        assert "about" in str(exc.value)
    
    def test_too_long_phone(self):
        """Тест слишком длинного телефона"""
        with pytest.raises(ValidationError) as exc:
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name="Test",
                phone="1" * 21
            )
        assert "phone" in str(exc.value)


class TestRegisterResponseDTO:
    """Тесты DTO ответа регистрации"""
    
    def test_valid_response(self):
        """Тест валидного ответа"""
        dto = RegisterResponseDTO(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            message="User registered successfully"
        )
        assert dto.user_id == "123e4567-e89b-12d3-a456-426614174000"
        assert dto.message == "User registered successfully"
    
    def test_default_message(self):
        """Тест сообщения по умолчанию"""
        dto = RegisterResponseDTO(user_id="123e4567-e89b-12d3-a456-426614174000")
        assert dto.message == "User registered successfully"
    
    def test_custom_message(self):
        """Тест кастомного сообщения"""
        dto = RegisterResponseDTO(
            user_id="123",
            message="Custom message"
        )
        assert dto.message == "Custom message"
    
    def test_invalid_uuid(self):
        """Тест невалидного UUID (принимает любую строку)"""
        dto = RegisterResponseDTO(user_id="not-a-uuid")
        assert dto.user_id == "not-a-uuid"


class TestLoginRequestDTO:
    """Тесты DTO логина"""
    
    def test_login_with_email(self):
        """Тест логина по email"""
        dto = LoginRequestDTO(
            login="test@example.com",
            password="SecurePass123!"
        )
        assert dto.login == "test@example.com"
        assert dto.password == "SecurePass123!"
    
    def test_login_with_username(self):
        """Тест логина по username"""
        dto = LoginRequestDTO(
            login="testuser",
            password="SecurePass123!"
        )
        assert dto.login == "testuser"
    
    def test_login_with_email_alias(self):
        """Тест логина с алиасом email"""
        dto = LoginRequestDTO(
            email="test@example.com",
            password="SecurePass123!"
        )
        assert dto.login == "test@example.com"
    
    def test_login_too_short(self):
        """Тест короткого логина"""
        with pytest.raises(ValidationError) as exc:
            LoginRequestDTO(
                login="ab",
                password="SecurePass123!"
            )
        assert "login" in str(exc.value)
    
    def test_empty_password(self):
        """Тест пустого пароля"""
        with pytest.raises(ValidationError) as exc:
            LoginRequestDTO(
                login="test@example.com",
                password=""
            )
        assert "password" in str(exc.value)


class TestTokenResponseDTO:
    """Тесты DTO ответа с токенами"""
    
    def test_minimal_token_response(self):
        """Тест минимального ответа"""
        dto = TokenResponseDTO(
            access_token="access-token-123",
            expires_in=300
        )
        assert dto.access_token == "access-token-123"
        assert dto.expires_in == 300
        assert dto.token_type == "bearer"
        assert dto.refresh_expires_in is None
        assert dto.scope is None
        assert dto.user_id is None
    
    def test_full_token_response(self):
        """Тест полного ответа"""
        dto = TokenResponseDTO(
            access_token="access-token-123",
            expires_in=300,
            refresh_expires_in=1800,
            token_type="Bearer",
            scope="email profile",
            user_id="123e4567-e89b-12d3-a456-426614174000"
        )
        assert dto.access_token == "access-token-123"
        assert dto.expires_in == 300
        assert dto.refresh_expires_in == 1800
        assert dto.token_type == "Bearer"
        assert dto.scope == "email profile"
        assert dto.user_id == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_extra_fields_ignored(self):
        """Тест игнорирования лишних полей"""
        dto = TokenResponseDTO(
            access_token="token",
            expires_in=300,
            extra_field="should be ignored"  # type: ignore
        )
        assert not hasattr(dto, "extra_field")


class TestForgotPasswordRequestDTO:
    """Тесты DTO забыл пароль"""
    
    def test_valid_email(self):
        """Тест валидного email"""
        dto = ForgotPasswordRequestDTO(email="test@example.com")
        assert dto.email == "test@example.com"
    
    def test_invalid_email(self):
        """Тест невалидного email"""
        with pytest.raises(ValidationError) as exc:
            ForgotPasswordRequestDTO(email="invalid-email")
        assert "email" in str(exc.value)
    
    def test_empty_email(self):
        """Тест пустого email"""
        with pytest.raises(ValidationError) as exc:
            ForgotPasswordRequestDTO(email="")
        assert "email" in str(exc.value)


class TestResetPasswordRequestDTO:
    """Тесты DTO сброса пароля"""
    
    def test_valid_reset_password(self):
        """Тест валидного сброса пароля"""
        dto = ResetPasswordRequestDTO(
            key="valid-reset-token-123",
            new_password="NewSecurePass123!"
        )
        assert dto.key == "valid-reset-token-123"
        assert dto.new_password == "NewSecurePass123!"
    
    def test_empty_key(self):
        """Тест пустого ключа"""
        with pytest.raises(ValidationError) as exc:
            ResetPasswordRequestDTO(
                key="",
                new_password="SecurePass123!"
            )
        assert "key" in str(exc.value)
    
    def test_weak_new_password(self):
        """Тест слабого нового пароля"""
        with pytest.raises(ValidationError) as exc:
            ResetPasswordRequestDTO(
                key="valid-token",
                new_password="123"
            )
        assert "new_password" in str(exc.value)
    
    def test_empty_new_password(self):
        """Тест пустого нового пароля"""
        with pytest.raises(ValidationError) as exc:
            ResetPasswordRequestDTO(
                key="valid-token",
                new_password=""
            )
        assert "new_password" in str(exc.value)


class TestVerifyEmailRequestDTO:
    """Тесты DTO верификации email"""
    
    def test_valid_key(self):
        """Тест валидного ключа"""
        dto = VerifyEmailRequestDTO(key="valid-verification-token-123")
        assert dto.key == "valid-verification-token-123"
    
    def test_empty_key(self):
        """Тест пустого ключа"""
        with pytest.raises(ValidationError) as exc:
            VerifyEmailRequestDTO(key="")
        assert "key" in str(exc.value)


class TestMeResponseDTO:
    """Тесты DTO ответа /me"""
    
    def test_minimal_response(self):
        """Тест минимального ответа"""
        dto = MeResponseDTO(sub="123e4567-e89b-12d3-a456-426614174000")
        assert dto.sub == "123e4567-e89b-12d3-a456-426614174000"
        assert dto.email is None
        assert dto.realm_roles == []
        assert dto.client_roles == {}
        assert dto.raw_claims == {}
    
    def test_full_response(self):
        """Тест полного ответа"""
        dto = MeResponseDTO(
            sub="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            preferred_username="testuser",
            name="Test User",
            given_name="Test",
            family_name="User",
            phone="+79001234567",
            about="Software Developer",
            realm_roles=["user", "admin"],
            client_roles={"account": ["view-profile"]},
            raw_claims={"custom": "claim"}
        )
        assert dto.sub == "123e4567-e89b-12d3-a456-426614174000"
        assert dto.email == "test@example.com"
        assert dto.preferred_username == "testuser"
        assert dto.name == "Test User"
        assert dto.given_name == "Test"
        assert dto.family_name == "User"
        assert dto.phone == "+79001234567"
        assert dto.about == "Software Developer"
        assert dto.realm_roles == ["user", "admin"]
        assert dto.client_roles == {"account": ["view-profile"]}
        assert dto.raw_claims == {"custom": "claim"}
    
    def test_default_factories(self):
        """Тест значений по умолчанию"""
        dto = MeResponseDTO(sub="123")
        assert dto.realm_roles == []
        assert dto.client_roles == {}
        assert dto.raw_claims == {}

