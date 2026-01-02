"""
Tests for exception detector.

Covers:
- Basic exception detection
- Message extraction
- Regex escaping for special characters
- Quote handling
- Long message truncation
- Test code generation
"""

import pytest
import textwrap 
from pytest_pipeline_mcp.core.generators.extractors.exception_detector import (
    detect_exceptions,
    escape_for_regex,
    format_match_string,
    generate_exception_test,
    DetectedException,
)


class TestEscapeForRegex:
    """Tests for escape_for_regex function."""
    
    def test_simple_message(self):
        """Test message with no special characters."""
        result = escape_for_regex("Invalid value")
        assert result == r"Invalid\ value"
    
    def test_parentheses(self):
        """Test message with parentheses - common regex chars."""
        result = escape_for_regex("Expected (x, y)")
        assert r"\(" in result
        assert r"\)" in result
        # Should be safely escaped
        assert result == r"Expected\ \(x,\ y\)"
    
    def test_brackets(self):
        """Test message with square brackets."""
        result = escape_for_regex("Index [0] out of range")
        assert r"\[" in result
        assert r"\]" in result
    
    def test_dollar_sign(self):
        """Test message with dollar sign."""
        result = escape_for_regex("Price must be $100")
        assert r"\$" in result
    
    def test_caret(self):
        """Test message with caret."""
        result = escape_for_regex("^invalid pattern")
        assert r"\^" in result
    
    def test_asterisk(self):
        """Test message with asterisk."""
        result = escape_for_regex("value * 2")
        assert r"\*" in result
    
    def test_plus(self):
        """Test message with plus."""
        result = escape_for_regex("a + b")
        assert r"\+" in result
    
    def test_question_mark(self):
        """Test message with question mark."""
        result = escape_for_regex("value?")
        assert r"\?" in result
    
    def test_dot(self):
        """Test message with dot."""
        result = escape_for_regex("file.txt")
        assert r"\." in result
    
    def test_pipe(self):
        """Test message with pipe (OR in regex)."""
        result = escape_for_regex("a | b")
        assert r"\|" in result
    
    def test_backslash(self):
        """Test message with backslash."""
        result = escape_for_regex("path\\to\\file")
        assert "\\\\" in result  # Escaped backslash
    
    def test_comparison_operators(self):
        """Test messages with comparison operators.
        
        Note: >, <, = are NOT regex special characters,
        so re.escape() correctly does NOT escape them.
        """
        result = escape_for_regex("must be >= 0")
        # These are not regex metacharacters, so not escaped
        assert ">=" in result
        # But spaces are escaped
        assert r"\ " in result
        
        result = escape_for_regex("must be <= 100")
        assert "<=" in result
    
    def test_curly_braces(self):
        """Test message with curly braces."""
        result = escape_for_regex("format {key}")
        assert r"\{" in result
        assert r"\}" in result
    
    def test_truncation(self):
        """Test long message truncation."""
        long_message = "This is a very long error message that should be truncated"
        result = escape_for_regex(long_message, max_length=20)
        assert len(result) <= 20
    
    def test_empty_message(self):
        """Test empty message."""
        result = escape_for_regex("")
        assert result == ""
    
    def test_all_special_chars(self):
        """Test message with many special characters."""
        # Use shorter message to avoid truncation
        message = "(x + y) * [z] $?"
        result = escape_for_regex(message)
        # All special chars should be escaped
        assert r"\(" in result
        assert r"\)" in result
        assert r"\+" in result
        assert r"\*" in result
        assert r"\[" in result
        assert r"\]" in result
        assert r"\$" in result
        assert r"\?" in result


class TestFormatMatchString:
    """Tests for format_match_string function."""
    
    def test_simple_message(self):
        """Test simple message formatting."""
        result = format_match_string("Invalid value")
        assert result == r'match=r"Invalid\ value"'
    
    def test_message_with_double_quotes(self):
        """Test message containing double quotes."""
        result = format_match_string('Expected "value"')
        # Should use single quotes for the string
        assert result.startswith("match=r'")
    
    def test_message_with_single_quotes(self):
        """Test message containing single quotes."""
        result = format_match_string("Expected 'value'")
        # Should use double quotes for the string
        assert result.startswith('match=r"')
    
    def test_message_with_both_quotes(self):
        """Test message containing both quote types."""
        result = format_match_string("Expected 'x' or \"y\"")
        # Should escape double quotes and use double quote string
        assert 'match=r"' in result
    
    def test_empty_message(self):
        """Test empty message returns empty string."""
        result = format_match_string("")
        assert result == ""
    
    def test_none_message(self):
        """Test None message returns empty string."""
        result = format_match_string(None)
        assert result == ""
    
    def test_special_chars_are_escaped(self):
        """Test special characters are properly escaped."""
        result = format_match_string("Expected (x, y)")
        assert r"\(" in result
        assert r"\)" in result


class TestGenerateExceptionTest:
    """Tests for generate_exception_test function."""
    
    def test_simple_exception(self):
        """Test generating test for simple exception."""
        exc = DetectedException(
            exception_type="ValueError",
            condition=None,
            message=None
        )
        lines = generate_exception_test("my_func", exc, "0")
        
        assert len(lines) == 2
        assert lines[0] == "with pytest.raises(ValueError):"
        assert "my_func(0)" in lines[1]
    
    def test_exception_with_message(self):
        """Test generating test for exception with message."""
        exc = DetectedException(
            exception_type="ValueError",
            condition=None,
            message="Invalid input"
        )
        lines = generate_exception_test("my_func", exc, "0")
        
        assert "ValueError" in lines[0]
        assert "match=" in lines[0]
        assert "Invalid" in lines[0]
    
    def test_exception_with_special_chars_in_message(self):
        """Test message with regex special characters is escaped."""
        exc = DetectedException(
            exception_type="ValueError",
            condition=None,
            message="Expected (x, y) format"
        )
        lines = generate_exception_test("parse_point", exc, "'invalid'")
        
        # Should have escaped parentheses
        assert r"\(" in lines[0] or "match=r" in lines[0]
        # Should NOT have unescaped regex chars
        assert "match=\"Expected (x, y)" not in lines[0]  # Would break regex
    
    def test_exception_no_params(self):
        """Test generating test with no parameters."""
        exc = DetectedException(
            exception_type="RuntimeError",
            condition=None,
            message=None
        )
        lines = generate_exception_test("my_func", exc, "")
        
        assert "my_func()" in lines[1]
    
    def test_exception_multiple_params(self):
        """Test generating test with multiple parameters."""
        exc = DetectedException(
            exception_type="ValueError",
            condition=None,
            message="out of range"
        )
        lines = generate_exception_test("calculate", exc, "100, -1, 'test'")
        
        assert "calculate(100, -1, 'test')" in lines[1]
    
    def test_generated_code_is_valid_python(self):
        """Test that generated code is syntactically valid."""
        test_cases = [
            DetectedException("ValueError", None, "simple"),
            DetectedException("ValueError", None, "has (parens)"),
            DetectedException("ValueError", None, "has [brackets]"),
            DetectedException("ValueError", None, "has $dollar"),
            DetectedException("ValueError", None, "has * asterisk"),
            DetectedException("TypeError", None, None),
        ]
        
        for exc in test_cases:
            lines = generate_exception_test("func", exc, "x")
            code = "\n".join(lines)
            
            # Should be valid Python syntax when wrapped in a function
            full_code = f"import pytest\ndef test():\n    " + code.replace("\n", "\n    ")
            try:
                compile(full_code, "<test>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Generated invalid code for message '{exc.message}': {e}\nCode: {code}")
    def test_detect_exceptions_captures_if_condition(self):
        code = textwrap.dedent("""
        def divide(a: float, b: float) -> float:
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        """)

        excs = detect_exceptions(code, "divide")
        assert len(excs) == 1
        assert excs[0].condition is not None 


class TestDetectExceptions:
    """Tests for detect_exceptions function."""
    
    def test_detect_simple_raise(self):
        """Test detecting simple raise statement."""
        code = '''
def my_func(x):
    if x < 0:
        raise ValueError("x must be positive")
    return x
'''
        exceptions = detect_exceptions(code, "my_func")
        
        assert len(exceptions) == 1
        assert exceptions[0].exception_type == "ValueError"
        assert exceptions[0].message == "x must be positive"
    
    def test_detect_multiple_raises(self):
        """Test detecting multiple raise statements."""
        code = '''
def validate(x, y):
    if x < 0:
        raise ValueError("x must be positive")
    if y is None:
        raise TypeError("y cannot be None")
    return x + y
'''
        exceptions = detect_exceptions(code, "validate")
        
        assert len(exceptions) == 2
        types = {e.exception_type for e in exceptions}
        assert types == {"ValueError", "TypeError"}
    
    def test_detect_raise_without_message(self):
        """Test detecting raise without message."""
        code = '''
def my_func(x):
    if x < 0:
        raise ValueError
    return x
'''
        exceptions = detect_exceptions(code, "my_func")
        
        assert len(exceptions) == 1
        assert exceptions[0].exception_type == "ValueError"
        assert exceptions[0].message is None
    
    def test_no_raise_statements(self):
        """Test function with no raise statements."""
        code = '''
def simple(x):
    return x * 2
'''
        exceptions = detect_exceptions(code, "simple")
        
        assert len(exceptions) == 0
    
    def test_function_not_found(self):
        """Test when function is not found."""
        code = '''
def other_func(x):
    raise ValueError("error")
'''
        exceptions = detect_exceptions(code, "my_func")
        
        assert len(exceptions) == 0
    
    def test_syntax_error_returns_empty(self):
        """Test that syntax error returns empty list."""
        code = "def broken( return"
        exceptions = detect_exceptions(code, "broken")
        
        assert exceptions == []
    
    def test_detect_exception_with_special_chars(self):
        """Test detecting exception with special characters in message."""
        code = '''
def parse_point(s):
    if not s:
        raise ValueError("Expected (x, y) format")
    return s
'''
        exceptions = detect_exceptions(code, "parse_point")
        
        assert len(exceptions) == 1
        assert exceptions[0].message == "Expected (x, y) format"


class TestIntegration:
    """Integration tests combining detection and test generation."""
    
    def test_full_pipeline_special_chars(self):
        """Test full pipeline with special characters in message."""
        code = '''
def validate_format(s):
    if "[" not in s:
        raise ValueError("Expected [key] format")
    return s
'''
        # Detect
        exceptions = detect_exceptions(code, "validate_format")
        assert len(exceptions) == 1
        
        # Generate
        lines = generate_exception_test("validate_format", exceptions[0], '"invalid"')
        
        # Verify it's valid Python
        full_code = f"import pytest\ndef test():\n    " + "\n    ".join(lines)
        compile(full_code, "<test>", "exec")  # Should not raise
        
        # Verify escaping
        assert r"\[" in lines[0] or "match=r" in lines[0]
    
    def test_full_pipeline_comparison_operators(self):
        """Test full pipeline with comparison operators."""
        code = '''
def validate_range(x):
    if not (0 <= x <= 100):
        raise ValueError("x must be >= 0 and <= 100")
    return x
'''
        exceptions = detect_exceptions(code, "validate_range")
        assert len(exceptions) == 1
        
        lines = generate_exception_test("validate_range", exceptions[0], "-1")
        
        # Verify it's valid Python
        full_code = f"import pytest\ndef test():\n    " + "\n    ".join(lines)
        compile(full_code, "<test>", "exec")
    
    def test_full_pipeline_parentheses(self):
        """Test full pipeline with parentheses - common edge case."""
        code = '''
def parse_tuple(s):
    raise ValueError("Expected (a, b) tuple")
'''
        exceptions = detect_exceptions(code, "parse_tuple")
        lines = generate_exception_test("parse_tuple", exceptions[0], '"bad"')
        
        # Verify valid Python
        full_code = f"import pytest\ndef test():\n    " + "\n    ".join(lines)
        compile(full_code, "<test>", "exec")
        
        # Verify parentheses are escaped
        match_line = lines[0]
        assert r"\(" in match_line
        assert r"\)" in match_line