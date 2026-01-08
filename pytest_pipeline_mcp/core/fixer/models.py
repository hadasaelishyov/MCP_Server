"""Dataclasses and types for the code fixer results."""

from dataclasses import dataclass, field
from typing import Literal

# Confidence levels for fixes
ConfidenceLevel = Literal["high", "medium", "low"]

# Severity levels for bugs
SeverityLevel = Literal["critical", "high", "medium", "low"]


@dataclass
class BugInfo:
    """A bug identified from failing tests (optional line number/severity/test name)."""
    
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
    """A single change applied to the code, with a short reason and optional location/snippets."""
    
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
    """Outcome of verifying a fix by re-running tests (counts + optional error)."""
    
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
    """Parsed failure details used to build the AI prompt (internal)."""
    
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
    """Result of a fix attempt: fixed code, bugs/fixes, optional verification, and confidence."""
    
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
                lines.append(f"Verified: All {self.verification.tests_passed} tests pass")
            else:
                lines.append(f"Verification: {self.verification.tests_passed}/{self.verification.tests_total} tests pass")

        return "\n".join(lines)
