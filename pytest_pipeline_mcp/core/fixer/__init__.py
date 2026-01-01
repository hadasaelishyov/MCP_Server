"""Code Fixer - Automatically fix bugs based on test failures.(AI-assisted bug fixing + verification)."""

from .fixer import CodeFixer, create_fixer, fix_code
from .models import (
    BugInfo,
    ConfidenceLevel,
    FailureInfo,
    FixInfo,
    FixResult,
    SeverityLevel,
    VerificationResult,
)

__all__ = [
    # Models
    "BugInfo",
    "FixInfo",
    "FixResult",
    "FailureInfo",
    "VerificationResult",
    "ConfidenceLevel",
    "SeverityLevel",
    # Fixer
    "CodeFixer",
    "fix_code",
    "create_fixer",
]
