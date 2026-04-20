"""Common exception types used across auth service."""


class AuthServiceError(Exception):
    """Base exception for auth service domain errors."""


class AuthProviderConflictError(AuthServiceError):
    """User already exists in the auth provider."""


class UserAlreadyExistsError(AuthServiceError):
    """User already exists in the auth service domain."""


class InvalidTokenError(AuthServiceError):
    """Provided action token is invalid or expired."""


class UserNotFoundError(AuthServiceError):
    """Target user was not found in auth provider."""


class KeycloakError(AuthServiceError):
    """Generic Keycloak integration error."""


class KeycloakUnavailableError(KeycloakError):
    """Keycloak is temporarily unavailable."""


class KeycloakConflictError(AuthProviderConflictError):
    """Conflict returned by Keycloak (e.g. existing user)."""
