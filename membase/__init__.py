"""Membase — long-term memory for AI. ``pip install membase-ai``.

from membase import Membase
client = Membase()  # MEMBASE_API_KEY
"""

from ._version import __version__
from .client import DEFAULT_BASE_URL, Membase
from .errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    MembaseError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "Membase",
    "MembaseError",
    "APIConnectionError",
    "APITimeoutError",
    "APIStatusError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "InternalServerError",
    "__version__",
]
