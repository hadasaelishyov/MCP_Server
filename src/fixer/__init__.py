"""
Code Fixer - Automatically fix bugs based on test failures.

This module analyzes test failures and uses AI to generate fixes
for the source code, then verifies the fixes work.
"""

from .models import (
    BugInfo,
    FixInfo,
    FixResult,
    FailureInfo,
    VerificationResult,
    ConfidenceLevel,
    SeverityLevel,
)
from .code_fixer import CodeFixer, fix_code, create_fixer

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