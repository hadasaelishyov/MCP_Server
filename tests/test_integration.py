"""
Integration tests - test the complete pipeline.

These tests verify that all components work together correctly.
"""

import pytest
from src.analyzer import analyze_code
from src.generators import generate_tests
from src.runner import run_tests


class TestFullPipeline:
    """Test the complete analyze → generate → run pipeline."""

    def test_simple_function_pipeline(self):
        """Test pipeline with a simple correct function."""
        source = '''
def add(a: int, b: int) -> int:
    """Add two numbers.
    
    >>> add(1, 2)
    3
    """
    return a + b
'''
        # Step 1: Analyze
        analysis = analyze_code(source)
        assert analysis.valid is True
        assert len(analysis.functions) == 1
        assert analysis.functions[0].name == "add"

        # Step 2: Generate tests
        result = generate_tests(analysis, source, module_name="test_module")
        assert len(result.test_cases) > 0
        
        # Should have doctest-based test
        doctest_tests = [t for t in result.test_cases if t.evidence_source == "doctest"]
        assert len(doctest_tests) >= 1

        # Step 3: Run tests
        test_code = result.to_code()
        run_result = run_tests(source, test_code)
        
        assert run_result.success is True
        assert run_result.passed > 0
        assert run_result.failed == 0

    def test_buggy_code_pipeline(self):
        """Test pipeline with buggy code (tests should fail)."""
        source = '''
def add(a: int, b: int) -> int:
    """Add two numbers.
    
    >>> add(1, 2)
    3
    """
    return a - b  # BUG: should be +
'''
        # Step 1: Analyze (syntax is valid)
        analysis = analyze_code(source)
        assert analysis.valid is True

        # Step 2: Generate tests
        result = generate_tests(analysis, source, module_name="test_module")
        assert len(result.test_cases) > 0

        # Step 3: Run tests (should fail due to bug)
        test_code = result.to_code()
        run_result = run_tests(source, test_code)
        
        # The doctest test should fail because add(1,2) returns -1, not 3
        assert run_result.failed > 0 or run_result.success is False

    def test_exception_detection_pipeline(self):
        """Test that exception tests are generated and work."""
        source = '''
def divide(a: float, b: float) -> float:
    """Divide a by b.
    
    Raises:
        ValueError: If b is zero.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
        # Analyze
        analysis = analyze_code(source)
        assert analysis.valid is True

        # Generate tests
        result = generate_tests(analysis, source, module_name="test_module")
        
        # Should have exception test
        exception_tests = [t for t in result.test_cases if t.evidence_source == "exception"]
        assert len(exception_tests) >= 1
        
        # Verify "pytest.raises" is in the test
        test_code = result.to_code()
        assert "pytest.raises(ValueError" in test_code

    def test_class_pipeline(self):
        """Test pipeline with a class."""
        source = '''
class Calculator:
    """A simple calculator."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b
'''
        # Analyze
        analysis = analyze_code(source)
        assert analysis.valid is True
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "Calculator"

        # Generate tests
        result = generate_tests(analysis, source, module_name="test_module")
        
        # Should have class creation test
        test_names = [t.name for t in result.test_cases]
        assert "test_calculator_creation" in test_names

        # Run tests
        test_code = result.to_code()
        run_result = run_tests(source, test_code)
        
        assert run_result.success is True

    def test_empty_code_handled(self):
        """Test that empty code is handled gracefully."""
        analysis = analyze_code("")
        assert analysis.valid is False
        assert analysis.error is not None

    def test_syntax_error_handled(self):
        """Test that syntax errors are handled gracefully."""
        source = "def broken( return"
        analysis = analyze_code(source)
        assert analysis.valid is False
        assert "syntax" in analysis.error.lower() or "error" in analysis.error.lower()

    def test_type_hints_affect_generation(self):
        """Test that type hints lead to type assertion tests."""
        source = '''
def get_name() -> str:
    """Return a name."""
    return "Alice"
'''
        analysis = analyze_code(source)
        result = generate_tests(analysis, source, module_name="test_module")
        
        # Should have type hint test
        type_tests = [t for t in result.test_cases if t.evidence_source == "type_hint"]
        assert len(type_tests) >= 1
        
        # Verify isinstance check is present
        test_code = result.to_code()
        assert "isinstance(result, str)" in test_code