"""Тесты для main.py"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check_healthy():
    """Тест health check - здоров"""
    with patch('main.get_auth_service') as mock_get_auth:
        mock_auth = AsyncMock()
        mock_auth.health_check = AsyncMock(return_value=True)
        mock_get_auth.return_value = mock_auth
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_health_check_unhealthy():
    """Тест health check - не здоров"""
    with patch('main.get_auth_service') as mock_get_auth:
        mock_auth = AsyncMock()
        mock_auth.health_check = AsyncMock(return_value=False)
        mock_get_auth.return_value = mock_auth
        
        response = client.get("/health")
        
        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"