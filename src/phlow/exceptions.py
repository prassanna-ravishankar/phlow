"""Exception classes for Phlow authentication."""


class PhlowError(Exception):
    """Base exception for Phlow errors."""

    def __init__(self, message: str, code: str = "PHLOW_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AuthenticationError(PhlowError):
    """Raised when authentication fails."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        super().__init__(message, code, 401)


class AuthorizationError(PhlowError):
    """Raised when authorization fails."""

    def __init__(self, message: str, code: str = "AUTHZ_ERROR"):
        super().__init__(message, code, 403)


class ConfigurationError(PhlowError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, code: str = "CONFIG_ERROR"):
        super().__init__(message, code, 500)


class TokenError(PhlowError):
    """Raised when token operations fail."""

    def __init__(self, message: str, code: str = "TOKEN_ERROR"):
        super().__init__(message, code, 401)


class RateLimitError(PhlowError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", code: str = "RATE_LIMIT"):
        super().__init__(message, code, 429)
