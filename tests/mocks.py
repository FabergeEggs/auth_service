"""Моки для тестов"""
from unittest.mock import AsyncMock
from typing import Optional, Dict, Any

class MockAuthProvider:
    """Мок для AuthProvider"""
    
    def __init__(self):
        self.create_user = AsyncMock(return_value="test-user-id-123")
        self.get_user_by_email = AsyncMock(return_value=None)
        self.login_with_email = AsyncMock(return_value={
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "expires_in": 300
        })
        self.login_with_username = AsyncMock(return_value={
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "expires_in": 300
        })
        self.refresh_token = AsyncMock(return_value={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 300
        })
        self.send_reset_password_email = AsyncMock()
        self.reset_password_with_action_token = AsyncMock()
        self.logout = AsyncMock()
        self.logout_all_sessions = AsyncMock()
        self.health_check = AsyncMock(return_value=True)
        self.close = AsyncMock()