"""Тесты для DTO и валидаторов"""
import pytest
from pydantic import ValidationError
from src.api.dto import (
    RegisterRequestDTO,
    LoginRequestDTO,
    ResetPasswordRequestDTO
)

class TestRegisterRequestDTO:
    """Тесты DTO регистрации"""
    
    def test_valid_registration(self, test_user_data):
        """Тест валидных данных регистрации"""
        dto = RegisterRequestDTO(**test_user_data)
        assert dto.email == test_user_data["email"]
        assert dto.first_name == test_user_data["first_name"]
    
    def test_invalid_email(self):
        """Тест невалидного email"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="invalid-email",
                password="Test123!@#",
                first_name="Test"
            )
    
    def test_weak_password(self):
        """Тест слабого пароля"""
        with pytest.raises(ValidationError):
            RegisterRequestDTO(
                email="test@example.com",
                password="123",
                first_name="Test"
            )

class TestResetPasswordRequestDTO:
    """Тесты DTO сброса пароля"""
    
    def test_valid_reset_password(self):
        """Тест валидного сброса пароля"""
        dto = ResetPasswordRequestDTO(
            key="valid-reset-token-123",
            new_password="NewTest123!@#",
            confirm_password="NewTest123!@#"
        )
        assert dto.new_password == "NewTest123!@#"
    
    def test_password_mismatch(self):
        """Тест несовпадающих паролей"""
        with pytest.raises(ValidationError):
            ResetPasswordRequestDTO(
                key="valid-token",
                new_password="Test123!@#",
                confirm_password="Different123!@#"
            )