"""Тесты для DTO и валидаторов"""
import pytest
from pydantic import ValidationError
from src.api.dto import (
    RegisterRequestDTO,
    LoginRequestDTO,
    ResetPasswordRequestDTO,
    ForgotPasswordRequestDTO,
    VerifyEmailRequestDTO
)


class TestRegisterRequestDTO:
    """Тесты DTO регистрации"""
    
    def test_valid_registration(self, test_user_data: dict):
        """Тест валидных данных регистрации"""
        dto = RegisterRequestDTO(**test_user_data)
        assert dto.email == test_user_data["email"]
        assert dto.first_name == test_user_data["first_name"]
    
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
        assert dto.last_name == "User"
        assert dto.phone == "+79001234567"
        assert dto.about == "Software Developer"
    
    def test_invalid_email(self):
        """Тест невалидного email"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="invalid-email",
                password="SecurePass123!",
                first_name="Test"
            )
    
    def test_weak_password(self):
        """Тест слабого пароля (меньше 6 символов)"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="test@example.com",
                password="123",
                first_name="Test"
            )
    
    def test_empty_first_name(self):
        """Тест пустого имени"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name=""
            )
    
    def test_too_long_first_name(self):
        """Тест слишком длинного имени"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="test@example.com",
                password="SecurePass123!",
                first_name="A" * 51  # max 50
            )


class TestLoginRequestDTO:
    """Тесты DTO логина"""
    
    def test_login_with_email(self):
        """Тест логина по email"""
        dto = LoginRequestDTO(
            login="test@example.com",
            password="SecurePass123!"
        )
        assert dto.login == "test@example.com"
    
    def test_login_with_username(self):
        """Тест логина по username"""
        dto = LoginRequestDTO(
            login="testuser",
            password="SecurePass123!"
        )
        assert dto.login == "testuser"
    
    def test_login_too_short(self):
        """Тест короткого логина"""
        with pytest.raises(ValidationError):
            LoginRequestDTO(
                login="ab",  # min 3
                password="SecurePass123!"
            )
    
    def test_empty_password(self):
        """Тест пустого пароля"""
        with pytest.raises(ValidationError):
            LoginRequestDTO(
                login="test@example.com",
                password=""
            )


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
        with pytest.raises(ValidationError):
            ResetPasswordRequestDTO(
                key="",
                new_password="SecurePass123!"
            )
    
    def test_weak_new_password(self):
        """Тест слабого нового пароля"""
        with pytest.raises(ValidationError):
            ResetPasswordRequestDTO(
                key="valid-token",
                new_password="123"
            )
    
    def test_empty_new_password(self):
        """Тест пустого нового пароля"""
        with pytest.raises(ValidationError):
            ResetPasswordRequestDTO(
                key="valid-token",
                new_password=""
            )


class TestForgotPasswordRequestDTO:
    """Тесты DTO забыл пароль"""
    
    def test_valid_email(self):
        """Тест валидного email"""
        dto = ForgotPasswordRequestDTO(email="test@example.com")
        assert dto.email == "test@example.com"
    
    def test_invalid_email(self):
        """Тест невалидного email"""
        with pytest.raises(ValidationError):
            ForgotPasswordRequestDTO(email="invalid-email")
    
    def test_empty_email(self):
        """Тест пустого email"""
        with pytest.raises(ValidationError):
            ForgotPasswordRequestDTO(email="")


class TestVerifyEmailRequestDTO:
    """Тесты DTO верификации email"""
    
    def test_valid_key(self):
        """Тест валидного ключа"""
        dto = VerifyEmailRequestDTO(key="valid-verification-token")
        assert dto.key == "valid-verification-token"
    
    def test_empty_key(self):
        """Тест пустого ключа"""
        with pytest.raises(ValidationError):
            VerifyEmailRequestDTO(key="")