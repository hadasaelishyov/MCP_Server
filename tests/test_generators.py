"""Tests for the test generator."""

import pytest
from src.core.analyzer import analyze_code
from src.core.generators import generate_tests, TemplateGenerator
from src.core.generators.base import GeneratedTestCase, GeneratedTest


class TestTemplateGenerator:
    """Tests for TemplateGenerator class."""

    def test_generate_basic_function(self):
        """Test generating tests for a simple function."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        assert len(result.test_cases) > 0
        assert "add" in result.imports
        
        # Should have basic test
        test_names = [t.name for t in result.test_cases]
        assert "test_add_basic" in test_names

    def test_generate_from_doctest(self):
        """Test that doctests are extracted and converted."""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers.
    
    >>> add(1, 2)
    3
    >>> add(0, 0)
    0
    """
    return a + b
'''
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        # Should have doctest-based tests
        doctest_tests = [t for t in result.test_cases if t.evidence_source == "doctest"]
        assert len(doctest_tests) == 2
        
        # Check assertions are correct
        assertions = [line for t in doctest_tests for line in t.body]
        assert "assert add(1, 2) == 3" in assertions
        assert "assert add(0, 0) == 0" in assertions

    def test_generate_type_assertions(self):
        """Test that type hints generate type assertions."""
        code = """
def get_name() -> str:
    return "hello"
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        # Should have type test
        type_tests = [t for t in result.test_cases if t.evidence_source == "type_hint"]
        assert len(type_tests) == 1
        assert "assert isinstance(result, str)" in type_tests[0].body

    def test_generate_exception_test(self):
        """Test that exceptions are detected and tested."""
        code = """
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        # Should have exception test
        exception_tests = [t for t in result.test_cases if t.evidence_source == "exception"]
        assert len(exception_tests) == 1
        assert "pytest.raises(ValueError" in exception_tests[0].body[0]

    def test_generate_boolean_naming_heuristic(self):
        """Test that is_* functions get boolean assertions."""
        code = """
def is_valid(x: str) -> bool:
    return len(x) > 0
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")

        # Should have naming heuristic test
        heuristic_tests = [t for t in result.test_cases if t.evidence_source == "naming_heuristic"]
        assert len(heuristic_tests) == 1
        
        # Check assertion is somewhere in the body
        body_text = "\n".join(heuristic_tests[0].body)
        assert "isinstance(result, bool)" in body_text

    def test_generate_boundary_tests(self):
        """Test that boundary value tests are generated."""
        code = """
def process(x: int) -> int:
    return x * 2
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module", include_edge_cases=True)
        
        # Should have boundary tests
        boundary_tests = [t for t in result.test_cases if t.evidence_source == "boundary"]
        assert len(boundary_tests) > 0

    def test_skip_edge_cases_when_disabled(self):
        """Test that edge cases can be disabled."""
        code = """
def process(x: int) -> int:
    return x * 2
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module", include_edge_cases=False)
        
        # Should NOT have boundary tests
        boundary_tests = [t for t in result.test_cases if t.evidence_source == "boundary"]
        assert len(boundary_tests) == 0

    def test_generate_for_class(self):
        """Test generating tests for a class."""
        code = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        return a - b
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        assert "Calculator" in result.imports
        
        # Should have class creation test
        test_names = [t.name for t in result.test_cases]
        assert "test_calculator_creation" in test_names

    def test_skip_private_functions(self):
        """Test that private functions are skipped."""
        code = """
def public_func():
    return 1

def _private_func():
    return 2
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="test_module")
        
        test_names = [t.name for t in result.test_cases]
        assert any("public_func" in name for name in test_names)
        assert not any("private_func" in name for name in test_names)

    def test_to_code_output(self):
        """Test that to_code produces valid Python."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        analysis = analyze_code(code)
        result = generate_tests(analysis, code, module_name="my_module")
        
        output = result.to_code()
        
        # Should have proper structure
        assert '"""Tests for my_module."""' in output
        assert "import pytest" in output
        assert "from my_module import add" in output
        assert "def test_add_basic():" in output


class TestEvidenceExtractors:
    """Tests for individual evidence extractors."""

    def test_doctest_extractor(self):
        """Test doctest extraction."""
        from src.core.generators.extractors.doctest_extractor import extract_doctests
        
        docstring = '''
        Add two numbers.
        
        >>> add(1, 2)
        3
        >>> add(0, 0)
        0
        '''
        
        examples = extract_doctests(docstring)
        assert len(examples) == 2
        assert examples[0].call == "add(1, 2)"
        assert examples[0].expected == "3"

    def test_type_assertions(self):
        """Test type assertion generation."""
        from src.core.generators.extractors.type_assertions import generate_type_assertions
        
        assertions = generate_type_assertions("int")
        assert "assert isinstance(result, int)" in assertions
        
        assertions = generate_type_assertions("list[str]")
        assert "assert isinstance(result, list)" in assertions

    def test_exception_detector(self):
        """Test exception detection."""
        from src.core.generators.extractors.exception_detector import detect_exceptions
        
        code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        exceptions = detect_exceptions(code, "divide")
        assert len(exceptions) == 1
        assert exceptions[0].exception_type == "ValueError"
        assert exceptions[0].message == "Cannot divide by zero"

    def test_boundary_values(self):
        """Test boundary value generation."""
        from src.core.generators.extractors.boundary_values import generate_boundary_values, get_default_value
        
        # Test default values
        assert get_default_value("int") == "0"
        assert get_default_value("str") == '""'
        assert get_default_value("list") == "[]"
        
        # Test boundary values
        boundaries = generate_boundary_values("int")
        values = [b.value for b in boundaries]
        assert "0" in values
        assert "-1" in values