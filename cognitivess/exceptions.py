"""Ierarhia de exceptii pentru SDK-ul Cognitivess.

Toate exceptiile ridicate de SDK mostenesc :class:`CognitivessError`.
"""


class CognitivessError(Exception):
    """Baza tuturor erorilor ridicate de SDK."""

    def __init__(self, message: str = "", *args):
        super().__init__(message, *args)
        self.message = message


class APIError(CognitivessError):
    """Eroare generica legata de API (retea, parsing, etc.)."""


class APIConnectionError(APIError):
    """Nu s-a putut conecta la server (DNS, refuz, offline)."""

    def __init__(self, message: str = "Connection error", *, cause=None):
        super().__init__(message)
        self.__cause__ = cause


class APITimeoutError(APIConnectionError):
    """Cererea a depasit timeout-ul configurat."""

    def __init__(self, message: str = "Request timed out", *, cause=None):
        super().__init__(message, cause=cause)


class APIStatusError(APIError):
    """Server-ul a raspuns cu un status code non-2xx."""

    def __init__(self, message: str, *, status_code: int, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AuthenticationError(APIStatusError):
    """API key invalid/revocat (401)."""

    def __init__(self, message: str, *, status_code: int = 401, body=None):
        super().__init__(message, status_code=status_code, body=body)


class RateLimitError(APIStatusError):
    """Ai depasit un limit de rate / credit (429)."""

    def __init__(self, message: str, *, status_code: int = 429, body=None):
        super().__init__(message, status_code=status_code, body=body)