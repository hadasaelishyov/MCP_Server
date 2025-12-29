"""
Data models for the code fixer module.

These models represent:
- Bugs found in the source code
- Fixes applied to correct the bugs
- Verification results after applying fixes
- Complete fix operation results
"""

from dataclasses import dataclass, field
from typing import Literal


# Confidence levels for fixes
ConfidenceLevel = Literal["high", "medium", "low"]

# Severity levels for bugs
SeverityLevel = Literal["critical", "high", "medium", "low"]


@dataclass
class BugInfo:
    """
    Information about a single bug found in the source code.
    
    Attributes:
        description: Human-readable description of the bug
        line_number: Line number where the bug occurs (if identifiable)
        severity: How severe the bug is
        test_name: Name of the test that revealed this bug
    """
    description: str
    line_number: int | None = None
    severity: SeverityLevel = "medium"
    test_name: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "description": self.description,
            "line_number": self.line_number,
            "severity": self.severity,
            "test_name": self.test_name,
        }


@dataclass
class FixInfo:
    """
    Information about a fix applied to the source code.
    
    Attributes:
        description: What was changed
        reason: Why this change fixes the bug
        line_number: Line number that was modified
        original_code: The original code snippet (optional)
        fixed_code: The fixed code snippet (optional)
    """
    description: str
    reason: str
    line_number: int | None = None
    original_code: str | None = None
    fixed_code: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "description": self.description,
            "reason": self.reason,
        }
        if self.line_number:
            result["line_number"] = self.line_number
        if self.original_code:
            result["original_code"] = self.original_code
        if self.fixed_code:
            result["fixed_code"] = self.fixed_code
        return result


@dataclass
class VerificationResult:
    """
    Result of verifying a fix by re-running tests.
    
    Attributes:
        ran: Whether verification was attempted
        passed: Whether all tests passed after the fix
        tests_total: Total number of tests run
        tests_passed: Number of tests that passed
        tests_failed: Number of tests that failed
        error_message: Error message if verification failed
    """
    ran: bool
    passed: bool = False
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    error_message: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ran": self.ran,
            "passed": self.passed,
            "tests_total": self.tests_total,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "error_message": self.error_message,
        }


@dataclass
class FailureInfo:
    """
    Information about a single test failure (used internally).
    
    Extracted from test output to provide context to AI.
    
    Attributes:
        test_name: Name of the failed test
        error_type: Type of error (AssertionError, ValueError, etc.)
        error_message: The error message
        expected: Expected value (if assertion failure)
        actual: Actual value (if assertion failure)
        traceback: Relevant traceback lines
    """
    test_name: str
    error_type: str
    error_message: str
    expected: str | None = None
    actual: str | None = None
    traceback: list[str] = field(default_factory=list)
    
    def to_prompt_string(self) -> str:
        """Format failure info for AI prompt."""
        lines = [
            f"Test: {self.test_name}",
            f"Error: {self.error_type}: {self.error_message}",
        ]
        if self.expected and self.actual:
            lines.append(f"Expected: {self.expected}")
            lines.append(f"Actual: {self.actual}")
        if self.traceback:
            lines.append("Traceback:")
            for tb_line in self.traceback[:5]:  # Limit traceback lines
                lines.append(f"  {tb_line}")
        return "\n".join(lines)


@dataclass
class FixResult:
    """
    Complete result of a fix operation.
    
    Attributes:
        success: Whether the fix was successfully generated
        fixed_code: The corrected source code (if successful)
        bugs_found: List of bugs identified
        fixes_applied: List of fixes applied
        verification: Result of re-running tests
        confidence: Confidence level in the fix
        error: Error message if fix failed
        original_code: The original source code (for reference)
    """
    success: bool
    fixed_code: str | None = None
    bugs_found: list[BugInfo] = field(default_factory=list)
    fixes_applied: list[FixInfo] = field(default_factory=list)
    verification: VerificationResult | None = None
    confidence: ConfidenceLevel = "medium"
    error: str | None = None
    original_code: str | None = None
    
    @property
    def num_bugs(self) -> int:
        """Number of bugs found."""
        return len(self.bugs_found)
    
    @property
    def num_fixes(self) -> int:
        """Number of fixes applied."""
        return len(self.fixes_applied)
    
    @property
    def is_verified(self) -> bool:
        """Whether the fix was verified to work."""
        return self.verification is not None and self.verification.passed
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "fixed_code": self.fixed_code,
            "bugs_found": [b.to_dict() for b in self.bugs_found],
            "fixes_applied": [f.to_dict() for f in self.fixes_applied],
            "verification": self.verification.to_dict() if self.verification else None,
            "confidence": self.confidence,
            "error": self.error,
            "summary": {
                "num_bugs": self.num_bugs,
                "num_fixes": self.num_fixes,
                "verified": self.is_verified,
            }
        }
    
    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        if not self.success:
            return f"Fix failed: {self.error}"
        
        lines = [
            f"Found {self.num_bugs} bug(s), applied {self.num_fixes} fix(es)",
            f"Confidence: {self.confidence}",
        ]
        
        if self.verification:
            if self.verification.passed:
                lines.append(f"✅ Verified: All {self.verification.tests_passed} tests pass")
            else:
                lines.append(f"⚠️ Verification: {self.verification.tests_passed}/{self.verification.tests_total} tests pass")
        
        return "\n".join(lines)