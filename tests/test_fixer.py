"""
Tests for the code fixer module.

Covers:
- Models (BugInfo, FixInfo, FixResult, etc.)
- Failure analysis parsing
- Prompt building
- Response parsing
- Verification
- Full pipeline (with mocked AI)
"""

try:
    import pytest
except ImportError:
    pytest = None

from unittest.mock import Mock, patch

from pytest_pipeline_mcp.core.fixer import (
    CodeFixer,
    fix_code,
    create_fixer,
    FixResult,
    BugInfo,
    FixInfo,
    FailureInfo,
    VerificationResult,
)


class TestModels:
    """Test data models."""
    
    def test_bug_info_creation(self):
        """Test BugInfo creation and to_dict."""
        bug = BugInfo(
            description="Wrong operator",
            line_number=10,
            severity="high",
            test_name="test_add"
        )
        
        assert bug.description == "Wrong operator"
        assert bug.line_number == 10
        assert bug.severity == "high"
        assert bug.test_name == "test_add"
        
        d = bug.to_dict()
        assert d["description"] == "Wrong operator"
        assert d["line_number"] == 10
    
    def test_fix_info_creation(self):
        """Test FixInfo creation and to_dict."""
        fix = FixInfo(
            description="Changed - to +",
            reason="Addition needs plus operator",
            line_number=5,
            original_code="a - b",
            fixed_code="a + b"
        )
        
        assert fix.description == "Changed - to +"
        assert fix.reason == "Addition needs plus operator"
        
        d = fix.to_dict()
        assert d["original_code"] == "a - b"
        assert d["fixed_code"] == "a + b"
    
    def test_verification_result(self):
        """Test VerificationResult."""
        v = VerificationResult(
            ran=True,
            passed=True,
            tests_total=5,
            tests_passed=5,
            tests_failed=0
        )
        
        assert v.ran is True
        assert v.passed is True
        assert v.tests_total == 5
        
        d = v.to_dict()
        assert d["passed"] is True
    
    def test_failure_info_to_prompt_string(self):
        """Test FailureInfo formats correctly for AI prompt."""
        failure = FailureInfo(
            test_name="test_add",
            error_type="AssertionError",
            error_message="assert -1 == 5",
            expected="5",
            actual="-1",
            traceback=["line 10: assert add(2, 3) == 5"]
        )
        
        prompt = failure.to_prompt_string()
        
        assert "test_add" in prompt
        assert "AssertionError" in prompt
        assert "Expected: 5" in prompt
        assert "Actual: -1" in prompt
        assert "Traceback:" in prompt
    
    def test_fix_result_properties(self):
        """Test FixResult properties."""
        result = FixResult(
            success=True,
            fixed_code="def add(a, b): return a + b",
            bugs_found=[
                BugInfo("Bug 1", line_number=1),
                BugInfo("Bug 2", line_number=2),
            ],
            fixes_applied=[
                FixInfo("Fix 1", "Reason 1"),
            ],
            verification=VerificationResult(ran=True, passed=True, tests_total=3, tests_passed=3),
            confidence="high"
        )
        
        assert result.num_bugs == 2
        assert result.num_fixes == 1
        assert result.is_verified is True
    
    def test_fix_result_to_summary(self):
        """Test FixResult summary generation."""
        result = FixResult(
            success=True,
            fixed_code="code",
            bugs_found=[BugInfo("Bug")],
            fixes_applied=[FixInfo("Fix", "Reason")],
            verification=VerificationResult(ran=True, passed=True, tests_total=2, tests_passed=2),
            confidence="high"
        )
        
        summary = result.to_summary()
        
        assert "1 bug(s)" in summary
        assert "1 fix(es)" in summary
        assert "high" in summary
        assert "✅" in summary
    
    def test_fix_result_failed_summary(self):
        """Test FixResult summary for failed fix."""
        result = FixResult(
            success=False,
            error="API key not configured"
        )
        
        summary = result.to_summary()
        assert "failed" in summary.lower()
        assert "API key" in summary


class TestCodeFixerInit:
    """Test CodeFixer initialization."""
    
    def test_create_without_api_key(self):
        """Test creation without API key."""
        import os
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            fixer = CodeFixer()
            assert fixer.is_available() is False
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
    
    def test_create_with_api_key(self):
        """Test creation with API key."""
        fixer = CodeFixer()
        # Note: is_available() depends on openai package being installed
        assert fixer.model == "gpt-4o"
    
    def test_custom_model(self):
        """Test custom model setting."""
        fixer = CodeFixer(model="gpt-4o")
        assert fixer.model == "gpt-4o"
    
    def test_create_fixer_factory(self):
        """Test factory function."""
        fixer = create_fixer()
        assert isinstance(fixer, CodeFixer)


class TestFailureAnalysis:
    """Test failure analysis parsing."""
    
    def test_parse_pytest_format(self):
        """Test parsing pytest output format."""
        fixer = CodeFixer()
        
        output = """
test_calc.py::test_add FAILED
  Error: AssertionError: assert -1 == 5
test_calc.py::test_sub PASSED
test_calc.py::test_mul FAILED
  Error: TypeError: unsupported operand
"""
        failures = fixer._analyze_failures(output)
        
        assert len(failures) == 2
        assert failures[0].test_name == "test_add"
        assert failures[1].test_name == "test_mul"
    
    def test_parse_simple_format(self):
        """Test parsing simple format."""
        fixer = CodeFixer()
        
        output = """
test_add FAILED
  Error: AssertionError: assert 10 == 5
test_subtract FAILED
  Error: AssertionError: assert 0 == 2
"""
        failures = fixer._analyze_failures(output)
        
        assert len(failures) == 2
        assert failures[0].test_name == "test_add"
        assert failures[1].test_name == "test_subtract"
    
    def test_parse_with_traceback(self):
        """Test parsing with E lines (pytest traceback)."""
        fixer = CodeFixer()
        
        output = """
test_calc.py::test_divide FAILED
E       assert 0 == 5
E        +  where 0 = divide(10, 2)
"""
        failures = fixer._analyze_failures(output)
        
        assert len(failures) == 1
        assert failures[0].test_name == "test_divide"
        assert len(failures[0].traceback) >= 1
    
    def test_parse_no_failures(self):
        """Test parsing output with no failures."""
        fixer = CodeFixer()
        
        output = """
test_add PASSED
test_sub PASSED
"""
        failures = fixer._analyze_failures(output)
        
        assert len(failures) == 0
    
    def test_parse_empty_output(self):
        """Test parsing empty output."""
        fixer = CodeFixer()
        failures = fixer._analyze_failures("")
        assert len(failures) == 0


class TestPromptBuilding:
    """Test AI prompt building."""
    
    def test_build_prompt_contains_source(self):
        """Test prompt contains source code."""
        fixer = CodeFixer()
        
        source = "def add(a, b): return a - b"
        tests = "def test_add(): assert add(1, 2) == 3"
        failures = [FailureInfo("test_add", "AssertionError", "assert -1 == 3")]
        
        prompt = fixer._build_fix_prompt(source, tests, failures)
        
        assert "def add(a, b)" in prompt
        assert "return a - b" in prompt
    
    def test_build_prompt_contains_tests(self):
        """Test prompt contains test code."""
        fixer = CodeFixer()
        
        source = "def add(a, b): return a - b"
        tests = "def test_add(): assert add(1, 2) == 3"
        failures = [FailureInfo("test_add", "AssertionError", "assert -1 == 3")]
        
        prompt = fixer._build_fix_prompt(source, tests, failures)
        
        assert "def test_add()" in prompt
        assert "assert add(1, 2) == 3" in prompt
    
    def test_build_prompt_contains_failures(self):
        """Test prompt contains failure info."""
        fixer = CodeFixer()
        
        source = "def add(a, b): return a - b"
        tests = "def test_add(): assert add(1, 2) == 3"
        failures = [
            FailureInfo("test_add", "AssertionError", "assert -1 == 3"),
            FailureInfo("test_sub", "TypeError", "unsupported operand"),
        ]
        
        prompt = fixer._build_fix_prompt(source, tests, failures)
        
        assert "Failure 1" in prompt
        assert "Failure 2" in prompt
        assert "test_add" in prompt
        assert "test_sub" in prompt


class TestResponseParsing:
    """Test AI response parsing."""
    
    def test_parse_valid_response(self):
        """Test parsing a valid AI response."""
        fixer = CodeFixer()
        
        response = """
BUGS FOUND:
1. [Line 1] Wrong operator: - instead of +

FIXED CODE:
```python
def add(a, b):
    return a + b
```

FIXES APPLIED:
1. [Line 1] Changed - to + | Reason: Addition uses plus

CONFIDENCE: high
"""
        source = "def add(a, b): return a - b"
        fixed_code, bugs, fixes, confidence = fixer._parse_fix_response(response, source)
        
        assert fixed_code is not None
        assert "return a + b" in fixed_code
        assert len(bugs) == 1
        assert bugs[0].line_number == 1
        assert len(fixes) == 1
        assert confidence == "high"
    
    def test_parse_multiple_bugs(self):
        """Test parsing response with multiple bugs."""
        fixer = CodeFixer()
        
        response = """
BUGS FOUND:
1. [Line 2] Wrong operator in add
2. [Line 5] Wrong operator in multiply
3. [Line 8] Missing return statement

FIXED CODE:
```python
def add(a, b):
    return a + b
```

FIXES APPLIED:
1. Fixed add
2. Fixed multiply
3. Added return

CONFIDENCE: medium
"""
        fixed_code, bugs, fixes, confidence = fixer._parse_fix_response(response, "")
        
        assert len(bugs) == 3
        assert len(fixes) == 3
        assert confidence == "medium"
    
    def test_parse_low_confidence(self):
        """Test parsing low confidence response."""
        fixer = CodeFixer()
        
        response = """
BUGS FOUND:
1. Complex logic issue

FIXED CODE:
```python
def func(): pass
```

FIXES APPLIED:
1. Restructured logic

CONFIDENCE: low
"""
        _, _, _, confidence = fixer._parse_fix_response(response, "")
        assert confidence == "low"
    
    def test_parse_invalid_code_returns_none(self):
        """Test that invalid Python code returns None."""
        fixer = CodeFixer()
        
        response = """
FIXED CODE:
```python
def broken( syntax error here
```
"""
        fixed_code, _, _, _ = fixer._parse_fix_response(response, "")
        assert fixed_code is None
    
    def test_parse_no_code_block(self):
        """Test parsing response without code block."""
        fixer = CodeFixer()
        
        response = """
BUGS FOUND:
1. Some bug

No code block here!
"""
        fixed_code, bugs, _, _ = fixer._parse_fix_response(response, "")
        assert fixed_code is None
        assert len(bugs) == 1


class TestSystemPrompt:
    """Test system prompt content."""
    
    def test_system_prompt_contains_key_instructions(self):
        """Test system prompt has important instructions."""
        fixer = CodeFixer()
        prompt = fixer._get_system_prompt()
        
        assert "MINIMAL" in prompt or "minimal" in prompt
        assert "BUGS FOUND" in prompt
        assert "FIXED CODE" in prompt
        assert "FIXES APPLIED" in prompt
        assert "CONFIDENCE" in prompt


class TestFixCodeFunction:
    """Test the main fix_code function."""
    @pytest.mark.asyncio
    async def test_fix_code_no_api_key(self):
        """Test fix_code returns error without API key."""
        import os
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = await fix_code(
                source_code="def add(a, b): return a - b",
                test_code="def test_add(): assert add(1, 2) == 3"
            )
            
            assert result.success is False
            assert "API key" in result.error
            assert result.original_code is not None
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
                
    @pytest.mark.asyncio
    async def test_fix_code_preserves_original(self):
        """Test that original code is preserved in result."""
        import os
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            source = "def broken(): return x"
            result = await fix_code(source, "def test(): pass")
            
            assert result.original_code == source
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key


class TestIntegrationWithMockedAI:
    """Integration tests with mocked OpenAI."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        """Test full pipeline with mocked AI."""
        # Setup mock
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
BUGS FOUND:
1. [Line 1] Wrong operator: using - instead of +

FIXED CODE:
```python
def add(a, b):
    return a + b
```

FIXES APPLIED:
1. [Line 1] Changed "a - b" to "a + b" | Reason: Addition needs +

CONFIDENCE: high
"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create fixer with mocked client
        fixer = CodeFixer()
        fixer.client = mock_client  # Inject mock
        
        result = await fixer.fix(
            source_code="def add(a, b): return a - b",
            test_code="def test_add(): assert add(2, 3) == 5",
            test_output="test_add FAILED\n  Error: AssertionError: assert -1 == 5",
            verify=False  # Skip verification for this test
        )
        
        assert result.success is True
        assert result.fixed_code is not None
        assert "return a + b" in result.fixed_code
        assert len(result.bugs_found) == 1
        assert len(result.fixes_applied) == 1
        assert result.confidence == "high"
    
    @pytest.mark.asyncio
    async def test_pipeline_with_api_error(self):
        """Test pipeline handles API errors gracefully."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        fixer = CodeFixer()
        fixer.client = mock_client  # Inject mock
        
        result = await fixer.fix(
            source_code="def add(a, b): return a - b",
            test_code="def test_add(): assert add(2, 3) == 5",
            test_output="test_add FAILED",
            verify=False
        )
        
        assert result.success is False
        assert "API Error" in result.error or "Fix failed" in result.error


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_source_code(self):
        """Test with empty source code."""
        import os
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = await fix_code("", "def test(): pass")
            # Should fail due to no API key, but shouldn't crash
            assert result.success is False
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
                
    @pytest.mark.asyncio
    async def test_empty_test_code(self):
        """Test with empty test code."""
        import os
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = await fix_code("def add(a, b): return a + b", "")
            assert result.success is False
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
    
    def test_fix_result_to_dict(self):
        """Test FixResult serialization."""
        result = FixResult(
            success=True,
            fixed_code="def add(a, b): return a + b",
            bugs_found=[BugInfo("Bug 1", line_number=1)],
            fixes_applied=[FixInfo("Fix 1", "Reason 1", line_number=1)],
            verification=VerificationResult(ran=True, passed=True, tests_total=1, tests_passed=1),
            confidence="high"
        )
        
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["fixed_code"] is not None
        assert len(d["bugs_found"]) == 1
        assert len(d["fixes_applied"]) == 1
        assert d["verification"]["passed"] is True
        assert d["confidence"] == "high"
        assert d["summary"]["num_bugs"] == 1
        assert d["summary"]["verified"] is True
