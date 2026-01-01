"""Code fixing service.

Attempts to fix failing code given tests/output and returns FixResult in ServiceResult.
"""


from __future__ import annotations

# Import existing domain models and functions
from ..core.fixer import FixResult, fix_code
from .base import ErrorCode, ServiceResult


class FixingService:
    """Fix code based on failing tests (optionally verify by re-running)."""

    def fix(
        self,
        source_code: str,
        test_code: str,
        test_output: str | None = None,
        verify: bool = True,
        api_key: str | None = None
    ) -> ServiceResult[FixResult]:
        """Attempt to fix `source_code` using `test_code` (+ optional test output / verification)."""

        # Step 1: Validate inputs
        validation_error = self._validate_inputs(source_code, test_code)
        if validation_error:
            return validation_error

        # Step 2: Run fixer
        try:
            fix_result = fix_code(
                source_code=source_code,
                test_code=test_code,
                test_output=test_output,
                verify=verify,
                api_key=api_key
            )
        except Exception as e:
            return ServiceResult.fail(
                ErrorCode.EXECUTION_ERROR,
                f"Fix operation failed: {e}"
            )

        # Note: Even if fix_result.success is False, the service call succeeded.
        # The FixResult itself contains the error information.
        # This allows handlers to distinguish between:
        # - Service failures (network, validation, etc.)
        # - Fix failures (couldn't find a fix)

        return ServiceResult.ok(fix_result)

    def fix_and_get_code(
        self,
        source_code: str,
        test_code: str,
        test_output: str | None = None,
        verify: bool = True,
        api_key: str | None = None
    ) -> ServiceResult[str]:
        """Fix code and return only the fixed code string (fails if fix unsuccessful)."""

        result = self.fix(
            source_code=source_code,
            test_code=test_code,
            test_output=test_output,
            verify=verify,
            api_key=api_key
        )

        if not result.success:
            return ServiceResult.fail(
                result.error.code,
                result.error.message,
                result.error.details
            )

        fix_result = result.data

        if not fix_result.success:
            return ServiceResult.fail(
                ErrorCode.EXECUTION_ERROR,
                fix_result.error or "Fix failed"
            )

        if not fix_result.fixed_code:
            return ServiceResult.fail(
                ErrorCode.EXECUTION_ERROR,
                "No fixed code generated"
            )

        return ServiceResult.ok(fix_result.fixed_code)

    def _validate_inputs(
        self,
        source_code: str,
        test_code: str
    ) -> ServiceResult[FixResult] | None:
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
