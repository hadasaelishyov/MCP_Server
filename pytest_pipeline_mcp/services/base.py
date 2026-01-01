"""
Service Layer Base - Core utilities for service operations.

This module provides:
- ServiceResult: A generic result wrapper (success/failure)
- ServiceError: Structured error information
- ErrorCode: Standard error codes

Design principles:
- Python 3.10+ compatible (uses typing.Generic)
- No duplicate models - services return existing domain models
- Immutable and stateless
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

# Generic type for result data
T = TypeVar("T")


class ErrorCode(str, Enum):
    """
    Standard error codes for service operations.
    
    Using string enum for easy serialization.
    """
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
    """
    Structured error information.
    
    Immutable (frozen) to prevent accidental modification.
    
    Attributes:
        code: Error code for programmatic handling
        message: Human-readable error message
        details: Optional additional context
    """
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
    """
    Generic result wrapper for service operations.
    
    This is a discriminated union: either success with data,
    or failure with error. Never both, never neither.
    
    Immutable (frozen) to prevent accidental modification.
    
    Usage:
        # Success
        result = ServiceResult.ok(analysis_result)
        
        # Failure  
        result = ServiceResult.fail(ErrorCode.FILE_NOT_FOUND, "File not found")
        
        # Handling
        if result.success:
            process(result.data)
        else:
            handle_error(result.error)
    """
    success: bool
    data: T | None = None
    error: ServiceError | None = None

    @classmethod
    def ok(cls, data: T) -> ServiceResult[T]:
        """
        Create a successful result.
        
        Args:
            data: The result data (must not be None for success)
            
        Returns:
            ServiceResult with success=True and data set
        """
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(
        cls,
        code: ErrorCode,
        message: str,
        details: dict | None = None
    ) -> ServiceResult[T]:
        """
        Create a failed result.
        
        Args:
            code: Error code for programmatic handling
            message: Human-readable error message
            details: Optional additional context
            
        Returns:
            ServiceResult with success=False and error set
        """
        return cls(
            success=False,
            data=None,
            error=ServiceError(code=code, message=message, details=details)
        )

    def map(self, func) -> ServiceResult:
        """
        Transform the data if successful.
        
        Args:
            func: Function to apply to data
            
        Returns:
            New ServiceResult with transformed data, or same error
        """
        if self.success and self.data is not None:
            return ServiceResult.ok(func(self.data))
        return self

    def unwrap(self) -> T:
        """
        Get the data, raising if failed.
        
        Returns:
            The result data
            
        Raises:
            ValueError: If result is a failure
        """
        if not self.success or self.data is None:
            error_msg = self.error.message if self.error else "Unknown error"
            raise ValueError(f"Cannot unwrap failed result: {error_msg}")
        return self.data

    def unwrap_or(self, default: T) -> T:
        """
        Get the data or a default value.
        
        Args:
            default: Value to return if failed
            
        Returns:
            The result data or default
        """
        if self.success and self.data is not None:
            return self.data
        return default
