"""
Fixing Service - Business logic for automatic code fixing.

Wraps the fixer module with:
- Input validation
- Structured error handling via ServiceResult

Returns the existing FixResult model - no duplication.
"""

from __future__ import annotations

# Import existing domain models and functions
from ..core.fixer import FixResult, fix_code
from .base import ErrorCode, ServiceResult


class FixingService:
    """
    Service for automatically fixing buggy code.
    
    Orchestrates:
    1. Input validation
    2. AI-based code fixing
    3. Optional verification via test re-run
    
    This class is stateless - no dependencies needed.
    """

    def fix(
        self,
        source_code: str,
        test_code: str,
        test_output: str | None = None,
        verify: bool = True,
        api_key: str | None = None
    ) -> ServiceResult[FixResult]:
        """
        Fix buggy code based on failing tests.
        
        Args:
            source_code: Python source code (contains bugs)
            test_code: Pytest test code
            test_output: Raw pytest output (runs tests if not provided)
            verify: Whether to verify fix by re-running tests
            api_key: OpenAI API key (uses env var if not provided)
            
        Returns:
            ServiceResult containing FixResult
            
        Example:
            service = FixingService()
            result = service.fix(
                source_code="def add(a, b): return a - b",  # Bug!
                test_code="def test_add(): assert add(1, 2) == 3"
            )
            if result.success and result.data.success:
                print(result.data.fixed_code)
        """
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
        """
        Fix code and return just the fixed code string.
        
        Convenience method when you only need the fixed code.
        Returns error if fix was unsuccessful.
        
        Args:
            source_code: Python source code (contains bugs)
            test_code: Pytest test code
            test_output: Raw pytest output
            verify: Whether to verify fix
            api_key: OpenAI API key
            
        Returns:
            ServiceResult containing fixed code string
        """
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
        """
        Validate inputs and return error if invalid.
        
        Args:
            source_code: Source code to validate
            test_code: Test code to validate
            
        Returns:
            ServiceResult with error, or None if valid
        """
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
