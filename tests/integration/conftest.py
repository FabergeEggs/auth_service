"""Fixtures for integration tests (Keycloak, Kafka, …)."""

import os
from uuid import uuid4

import pytest
import pytest_asyncio

from src.adapters.keycloak_adapter import KeycloakAdapter
from src.config import settings


def _keycloak_integration_enabled() -> bool:
    return os.getenv("RUN_KEYCLOAK_INTEGRATION", "").lower() in (
        "1",
        "true",
        "yes",
    )


@pytest_asyncio.fixture
async def keycloak_adapter():
    """Real Keycloak adapter; skipped unless RUN_KEYCLOAK_INTEGRATION=1 and KC is up."""
    if not _keycloak_integration_enabled():
        pytest.skip(
            "Keycloak integration disabled. "
            "Start Keycloak and run: RUN_KEYCLOAK_INTEGRATION=1 uv run pytest tests/integration/test_keycloak_real.py"
        )

    adapter = KeycloakAdapter.from_settings(settings)
    try:
        if not await adapter.health_check():
            pytest.skip(
                f"Keycloak not reachable at {settings.keycloak_url} "
                f"(realm={settings.realm})"
            )
        yield adapter
    finally:
        await adapter.close()


@pytest.fixture
def test_user_data():
    """User payload for Keycloak create_user (unique username per test)."""
    suffix = uuid4().hex[:10]
    try:
        from faker import Faker

        fake = Faker()
        email = fake.email()
        return {
            "username": f"pytest_{suffix}",
            "email": email,
            "password": "Test123!@#",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number()[:20],
            "about": fake.text(max_nb_chars=100),
        }
    except ImportError:
        return {
            "username": f"pytest_{suffix}",
            "email": f"pytest_{suffix}@example.com",
            "password": "Test123!@#",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "about": "Test about me",
        }
