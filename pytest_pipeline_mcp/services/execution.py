"""Test execution service.

Runs generated pytest tests (including coverage) and returns RunResult in ServiceResult.
"""


from __future__ import annotations

# Import existing domain models and functions
from ..core.runner import RunResult, run_tests
from .base import ErrorCode, ServiceResult


class ExecutionService:
    """Execute pytest tests for given source + tests and return a RunResult."""
    
    def run(
        self,
        source_code: str,
        test_code: str
    ) -> ServiceResult[RunResult]:
        """Run pytest tests for the given source code and test code."""
        
        # Step 1: Validate inputs
        validation_error = self._validate_inputs(source_code, test_code)
        if validation_error:
            return validation_error

        # Step 2: Run tests
        try:
            run_result = run_tests(source_code, test_code)
        except Exception as e:
            return ServiceResult.fail(
                ErrorCode.EXECUTION_ERROR,
                f"Test execution failed: {e}"
            )

        # Step 3: Check for runner-level errors
        if run_result.error_message and run_result.total == 0:
            return ServiceResult.fail(
                ErrorCode.EXECUTION_ERROR,
                run_result.error_message
            )

        return ServiceResult.ok(run_result)

    def run_and_summarize(
        self,
        source_code: str,
        test_code: str
    ) -> ServiceResult[dict]:
        """Run tests and return a JSON-serializable summary."""

        result = self.run(source_code, test_code)

        if not result.success:
            return ServiceResult.fail(
                result.error.code,
                result.error.message,
                result.error.details
            )

        return ServiceResult.ok(result.data.to_dict())

    def _validate_inputs(
        self,
        source_code: str,
        test_code: str
    ) -> ServiceResult[RunResult] | None:
        """Validate inputs and return error if invalid."""
        
        if not source_code or not source_code.strip():
            return ServiceResult.fail(
                ErrorCode.MISSING_INPUT,
                "'source_code' is required and cannot be empty"
            )

        if not test_code or not test_code.strip():
            return ServiceResult.fail(
                ErrorCode.MISSING_INPUT,
                "'test_code' is required and cannot be empty"
            )

        return None
