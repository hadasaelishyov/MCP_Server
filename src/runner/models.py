"""Data models for test runner."""

from dataclasses import dataclass, field


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    error_message: str | None = None
    duration: float = 0.0


@dataclass
class CoverageResult:
    """Code coverage metrics."""
    percentage: float
    covered_lines: int
    total_lines: int
    missing_lines: list[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "percentage": round(self.percentage, 1),
            "covered_lines": self.covered_lines,
            "total_lines": self.total_lines,
            "missing_lines": self.missing_lines,
        }


@dataclass
class RunResult:
    """Complete test run result."""
    total: int
    passed: int
    failed: int
    errors: int
    test_results: list[TestResult]
    coverage: CoverageResult | None
    success: bool
    error_message: str | None = None
    
    @property
    def passed_tests(self) -> list[str]:
        return [t.name for t in self.test_results if t.passed]
    
    @property
    def failed_tests(self) -> list[dict]:
        return [
            {"name": t.name, "error": t.error_message}
            for t in self.test_results if not t.passed
        ]
    
    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
            },
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "coverage": self.coverage.to_dict() if self.coverage else None,
        }