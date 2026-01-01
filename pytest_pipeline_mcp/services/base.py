"""Service-layer primitives for uniform success/failure handling.

Defines ErrorCode, ServiceError, and ServiceResult[T].
"""


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

# Generic type for result data
T = TypeVar("T")


class ErrorCode(str, Enum):
    """Serializable error categories returned by services."""

    # Input validation
    VALIDATION_ERROR = "validation_error"
    MISSING_INPUT = "missing_input"

    # File operations
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_EXTENSION = "invalid_extension"

    # Code analysis
    SYNTAX_ERROR = "syntax_error"
    PARSE_ERROR = "parse_error"

    # AI operations
    AI_UNAVAILABLE = "ai_unavailable"
    AI_ERROR = "ai_error"

    # Execution
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"

    # GitHub operations
    GITHUB_AUTH_ERROR = "github_auth_error"
    GITHUB_REPO_NOT_FOUND = "github_repo_not_found"
    GITHUB_CLONE_ERROR = "github_clone_error"
    GITHUB_API_ERROR = "github_api_error"

    # General
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ServiceError:
    """Structured error details for a failed service call."""

    code: ErrorCode
    message: str
    details: dict | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    """Success/failure wrapper returned by services (data on success, error on failure)."""

    success: bool
    data: T | None = None
    error: ServiceError | None = None

    @classmethod
    def ok(cls, data: T) -> ServiceResult[T]:
        """Create a successful result."""
        
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(
        cls,
        code: ErrorCode,
        message: str,
        details: dict | None = None
    ) -> ServiceResult[T]:
        """Create a failed result."""
        return cls(
            success=False,
            data=None,
            error=ServiceError(code=code, message=message, details=details)
        )

    def map(self, func) -> ServiceResult:
        """Transform the data if successful."""
        
        if self.success and self.data is not None:
            return ServiceResult.ok(func(self.data))
        return self

    def unwrap(self) -> T:
        """Get the data, raising if failed."""
    
        if not self.success or self.data is None:
            error_msg = self.error.message if self.error else "Unknown error"
            raise ValueError(f"Cannot unwrap failed result: {error_msg}")
        return self.data

    def unwrap_or(self, default: T) -> T:
        """Get the data or a default value."""
        
        if self.success and self.data is not None:
            return self.data
        return default
