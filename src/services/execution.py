"""
Execution Service - Business logic for test execution.

Wraps the runner module with:
- Input validation
- Structured error handling via ServiceResult

Returns the existing RunResult model - no duplication.
"""

from __future__ import annotations

from .base import ServiceResult, ErrorCode

# Import existing domain models and functions
from ..tools.core.runner import run_tests, RunResult


class ExecutionService:
    """
    Service for executing pytest tests.
    
    Orchestrates:
    1. Input validation
    2. Test execution in isolated environment
    3. Coverage collection
    
    This class is stateless - no dependencies needed.
    """
    
    def run(
        self,
        source_code: str,
        test_code: str
    ) -> ServiceResult[RunResult]:
        """
        Execute tests against source code.
        
        Args:
            source_code: Python source code to test
            test_code: Pytest test code to execute
            
        Returns:
            ServiceResult containing RunResult
            
        Example:
            service = ExecutionService()
            result = service.run(
                source_code="def add(a, b): return a + b",
                test_code="def test_add(): assert add(1, 2) == 3"
            )
            if result.success:
                print(f"Passed: {result.data.passed}/{result.data.total}")
        """
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
        """
        Execute tests and return a summary dictionary.
        
        Convenience method for when you need JSON-serializable output.
        
        Args:
            source_code: Python source code to test
            test_code: Pytest test code to execute
            
        Returns:
            ServiceResult containing summary dict
        """
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
