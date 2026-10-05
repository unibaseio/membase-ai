"""Errors, one class per HTTP status class, all carrying the platform's error envelope."""

from __future__ import annotations

from typing import Any


class MembaseError(Exception):
    """Base class of everything this package raises."""

    def __init__(self, message: str, *, status: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body
        err = body.get("error") if isinstance(body, dict) else None
        err = err if isinstance(err, dict) else {}
        self.code: str = str(err.get("code") or "")
        self.details: Any = err.get("details")
        self.retryable: bool = bool(err.get("retryable", False))
        self.trace_id: str = str(err.get("trace_id") or "")

    def __str__(self) -> str:  # pragma: no cover - formatting
        bits = [self.message]
        if self.status is not None:
            bits.append(f"[{self.status}{' ' + self.code if self.code else ''}]")
        if self.trace_id:
            bits.append(f"trace_id={self.trace_id}")
        return " ".join(bits)


class APIConnectionError(MembaseError):
    """The request never got an answer (DNS, connection refused, reset)."""


class APITimeoutError(APIConnectionError):
    """The request ran past the client's timeout."""


class APIStatusError(MembaseError):
    """A non-2xx answer."""


class BadRequestError(APIStatusError):
    """400 — a malformed request: a missing ``q``, both ``content`` and ``url``, an ambiguous ``container``."""


class AuthenticationError(APIStatusError):
    """401 — the request carried no bearer at all."""


class PermissionDeniedError(APIStatusError):
    """403 (``code: unauthorized``) — an unknown, expired or revoked key; a container outside the key's reach; or a verb above its access level."""


class NotFoundError(APIStatusError):
    """404 — an unknown document or memory id."""


class ConflictError(APIStatusError):
    """409."""


class UnprocessableEntityError(APIStatusError):
    """422 — the account's memory cannot run a turn on this deployment (``capability_unavailable``: no agent container, no model), or a body FastAPI could not parse."""


class RateLimitError(APIStatusError):
    """429 — the account's turn budget is spent for now."""


class InternalServerError(APIStatusError):
    """5xx."""


_BY_STATUS: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def error_for(status: int, body: Any, fallback: str = "") -> APIStatusError:
    """The exception for a non-2xx answer."""
    err = body.get("error") if isinstance(body, dict) else None
    message = (err or {}).get("message") if isinstance(err, dict) else None
    if not message and isinstance(body, dict) and body.get("detail"):
        message = str(body["detail"])
    message = message or fallback or f"HTTP {status}"
    cls = _BY_STATUS.get(status) or (InternalServerError if status >= 500 else APIStatusError)
    return cls(message, status=status, body=body)
