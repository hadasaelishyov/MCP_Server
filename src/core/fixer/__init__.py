"""
Code Fixer - Automatically fix bugs based on test failures.

This module analyzes test failures and uses AI to generate fixes
for the source code, then verifies the fixes work.
"""

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
