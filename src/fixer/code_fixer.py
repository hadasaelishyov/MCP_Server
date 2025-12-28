"""
Code Fixer - Automatically fix bugs based on test failures.

Uses AI to analyze test failures and generate minimal fixes
for the source code, then verifies the fixes work.
"""

import os
import re

from .models import (
    BugInfo,
    FixInfo,
    FixResult,
    FailureInfo,
    VerificationResult,
    ConfidenceLevel,
)


class CodeFixer:
    """
    Analyzes test failures and generates fixes for source code.
    
    Uses AI to understand what went wrong and propose minimal fixes.
    Optionally verifies fixes by re-running tests.
    """
    
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        """
        Initialize the code fixer.
        
        Args:
            api_key: OpenAI API key (or uses OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                pass  # OpenAI not installed
    
    def is_available(self) -> bool:
        """Check if AI fixing is available."""
        return self.client is not None
    
    def fix(
        self,
        source_code: str,
        test_code: str,
        test_output: str | None = None,
        verify: bool = True
    ) -> FixResult:
        """
        Analyze test failures and fix the source code.
        
        Args:
            source_code: The buggy Python source code
            test_code: The pytest test code
            test_output: Raw pytest output (if None, will run tests first)
            verify: Whether to verify the fix by re-running tests
            
        Returns:
            FixResult with fixed code, bugs found, and verification
        """
        # Check if AI is available
        if not self.is_available():
            return FixResult(
                success=False,
                error="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
                original_code=source_code
            )
        
        try:
            # Step 1: Run tests if no output provided
            if test_output is None:
                from ..runner import run_tests
                run_result = run_tests(source_code, test_code)
                
                # If all tests pass, nothing to fix!
                if run_result.success:
                    return FixResult(
                        success=True,
                        fixed_code=source_code,
                        bugs_found=[],
                        fixes_applied=[],
                        verification=VerificationResult(
                            ran=True,
                            passed=True,
                            tests_total=run_result.total,
                            tests_passed=run_result.passed,
                            tests_failed=run_result.failed
                        ),
                        confidence="high",
                        original_code=source_code
                    )
                
                # Build test output from run result
                test_output = self._build_test_output(run_result)
            
            # Step 2: Analyze failures from test output
            failures = self._analyze_failures(test_output)
            
            if not failures:
                # No failures detected - maybe parsing issue
                return FixResult(
                    success=False,
                    error="Could not parse test failures from output. Tests may have passed or output format is unexpected.",
                    original_code=source_code
                )
            
            # Step 3: Build prompt and call AI
            prompt = self._build_fix_prompt(source_code, test_code, failures)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent fixes
                max_tokens=3000
            )
            
            ai_output = response.choices[0].message.content
            
            # Step 4: Parse AI response
            fixed_code, bugs_found, fixes_applied, confidence = self._parse_fix_response(
                ai_output, source_code
            )
            
            if not fixed_code:
                return FixResult(
                    success=False,
                    error="AI did not return valid fixed code",
                    original_code=source_code
                )
            
            # Step 5: Verify fix if requested
            verification = None
            if verify:
                verification = self._verify_fix(fixed_code, test_code)
            
            return FixResult(
                success=True,
                fixed_code=fixed_code,
                bugs_found=bugs_found,
                fixes_applied=fixes_applied,
                verification=verification,
                confidence=confidence,
                original_code=source_code
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                error=f"Fix failed: {str(e)}",
                original_code=source_code
            )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI."""
        return """You are a Python debugging expert. Your task is to fix bugs in Python code based on failing tests.

You will receive:
1. Python source code (with bugs)
2. Test code that tests the source
3. Test failure details (which tests failed and why)

Your job:
1. Analyze each test failure to understand what went wrong
2. Identify the bug(s) in the source code
3. Provide a MINIMAL fix - only change what's necessary
4. Explain each bug and fix clearly

IMPORTANT RULES:
- Make the SMALLEST change that fixes the bug
- Do NOT refactor or improve code style
- Do NOT add features or change behavior beyond fixing the bug
- Keep all function signatures the same
- Preserve comments and docstrings

OUTPUT FORMAT (follow exactly):

BUGS FOUND:
1. [Line N] Description of the bug
2. [Line M] Description of another bug (if any)

FIXED CODE:
```python
# The complete fixed source code here
```

FIXES APPLIED:
1. [Line N] What was changed: "original" → "fixed" | Reason: why this fixes the bug
2. [Line M] What was changed: "original" → "fixed" | Reason: why this fixes the bug

CONFIDENCE: high/medium/low
(high = simple obvious fix, medium = logic fix but clear, low = complex or uncertain)
"""
    
    def _build_test_output(self, run_result) -> str:
        """Build test output string from RunResult."""
        lines = []
        
        for test in run_result.test_results:
            if test.passed:
                lines.append(f"{test.name} PASSED")
            else:
                lines.append(f"{test.name} FAILED")
                if test.error_message:
                    lines.append(f"  Error: {test.error_message}")
        
        if run_result.error_message:
            lines.append(f"Error: {run_result.error_message}")
        
        return "\n".join(lines)
    
    def _analyze_failures(self, test_output: str) -> list[FailureInfo]:
        """
        Parse test output to extract failure details.
        
        Args:
            test_output: Raw pytest output or formatted failure info
            
        Returns:
            List of FailureInfo objects
        """
        failures = []
        lines = test_output.split('\n')
        
        current_test = None
        current_error_type = "AssertionError"
        current_error_msg = ""
        current_traceback = []
        expected = None
        actual = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detect test name with FAILED
            if 'FAILED' in line and 'test_' in line:
                # Save previous failure if exists
                if current_test:
                    failures.append(FailureInfo(
                        test_name=current_test,
                        error_type=current_error_type,
                        error_message=current_error_msg or "Test failed",
                        expected=expected,
                        actual=actual,
                        traceback=current_traceback
                    ))
                
                # Extract test name - handle pytest format: file.py::test_name FAILED
                # or simple format: test_name FAILED
                if '::' in line:
                    # Pytest format: extract after ::
                    match = re.search(r'::(test_\w+)', line)
                else:
                    # Simple format: just find test_*
                    match = re.search(r'\b(test_\w+)\b', line)
                
                if match:
                    current_test = match.group(1)
                    current_error_type = "AssertionError"
                    current_error_msg = ""
                    current_traceback = []
                    expected = None
                    actual = None
            
            # Detect error type
            elif current_test and ('Error:' in line or 'Exception:' in line):
                # Extract error type and message
                if ':' in line_stripped:
                    parts = line_stripped.split(':', 1)
                    error_part = parts[0].strip()
                    if 'Error' in error_part or 'Exception' in error_part:
                        current_error_type = error_part.split()[-1]  # Get last word (the error type)
                        if len(parts) > 1:
                            current_error_msg = parts[1].strip()
            
            # Detect assertion details (E lines in pytest)
            elif current_test and line_stripped.startswith('E '):
                error_content = line_stripped[2:].strip()
                current_traceback.append(error_content)
                
                # Try to extract expected/actual
                if 'assert' in error_content:
                    current_error_msg = error_content
                if '==' in error_content:
                    # Pattern: assert X == Y or where X = ... and Y = ...
                    match = re.search(r'assert\s+(\S+)\s*==\s*(\S+)', error_content)
                    if match:
                        actual = match.group(1)
                        expected = match.group(2)
            
            # Detect where X = ... patterns
            elif current_test and 'where' in line_stripped.lower():
                current_traceback.append(line_stripped)
            
            # Detect simple error messages after test name
            elif current_test and 'Error:' in line_stripped:
                current_error_msg = line_stripped
        
        # Don't forget the last failure
        if current_test:
            failures.append(FailureInfo(
                test_name=current_test,
                error_type=current_error_type,
                error_message=current_error_msg or "Test failed",
                expected=expected,
                actual=actual,
                traceback=current_traceback
            ))
        
        return failures
    
    def _build_fix_prompt(
        self,
        source_code: str,
        test_code: str,
        failures: list[FailureInfo]
    ) -> str:
        """Build the prompt for AI with all context."""
        
        # Format failures
        failures_text = "\n\n".join([
            f"### Failure {i+1}:\n{f.to_prompt_string()}"
            for i, f in enumerate(failures)
        ])
        
        prompt = f"""## Source Code (contains bugs):
```python
{source_code}
```

## Test Code:
```python
{test_code}
```

## Test Failures ({len(failures)} failing test(s)):

{failures_text}

---

Please analyze the failures and fix the source code. Remember:
- Make MINIMAL changes
- Only fix what's needed to pass the tests
- Keep the same function signatures and structure
"""
        return prompt
    
    def _parse_fix_response(
        self,
        ai_output: str,
        original_code: str
    ) -> tuple[str | None, list[BugInfo], list[FixInfo], ConfidenceLevel]:
        """
        Parse AI response to extract fixed code and explanations.
        
        Returns:
            Tuple of (fixed_code, bugs_found, fixes_applied, confidence)
        """
        fixed_code = None
        bugs_found = []
        fixes_applied = []
        confidence: ConfidenceLevel = "medium"
        
        # Extract fixed code block
        if "```python" in ai_output:
            start = ai_output.find("```python") + len("```python")
            end = ai_output.find("```", start)
            if end > start:
                fixed_code = ai_output[start:end].strip()
        elif "```" in ai_output:
            # Try generic code block
            start = ai_output.find("```") + len("```")
            end = ai_output.find("```", start)
            if end > start:
                fixed_code = ai_output[start:end].strip()
        
        # Validate fixed code is valid Python
        if fixed_code:
            try:
                compile(fixed_code, '<fix>', 'exec')
            except SyntaxError:
                fixed_code = None
        
        # Extract bugs found
        if "BUGS FOUND:" in ai_output:
            bugs_section = ai_output.split("BUGS FOUND:")[1]
            # Stop at next section
            for end_marker in ["FIXED CODE:", "```"]:
                if end_marker in bugs_section:
                    bugs_section = bugs_section.split(end_marker)[0]
                    break
            
            for line in bugs_section.strip().split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove number prefix
                    bug_text = re.sub(r'^[\d\.\-\)\]]+\s*', '', line)
                    
                    # Try to extract line number
                    line_num = None
                    line_match = re.search(r'\[Line\s*(\d+)\]', bug_text)
                    if line_match:
                        line_num = int(line_match.group(1))
                        bug_text = bug_text.replace(line_match.group(0), '').strip()
                    
                    if bug_text:
                        bugs_found.append(BugInfo(
                            description=bug_text,
                            line_number=line_num,
                            severity="high" if "critical" in bug_text.lower() else "medium"
                        ))
        
        # Extract fixes applied
        if "FIXES APPLIED:" in ai_output:
            fixes_section = ai_output.split("FIXES APPLIED:")[1]
            # Stop at next section
            for end_marker in ["CONFIDENCE:", "---"]:
                if end_marker in fixes_section:
                    fixes_section = fixes_section.split(end_marker)[0]
                    break
            
            for line in fixes_section.strip().split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    fix_text = re.sub(r'^[\d\.\-\)\]]+\s*', '', line)
                    
                    # Try to extract line number
                    line_num = None
                    line_match = re.search(r'\[Line\s*(\d+)\]', fix_text)
                    if line_match:
                        line_num = int(line_match.group(1))
                        fix_text = fix_text.replace(line_match.group(0), '').strip()
                    
                    # Try to split description and reason
                    reason = "Fixes failing test"
                    if '|' in fix_text:
                        parts = fix_text.split('|')
                        fix_text = parts[0].strip()
                        if len(parts) > 1:
                            reason_part = parts[1].strip()
                            if reason_part.lower().startswith('reason:'):
                                reason = reason_part[7:].strip()
                            else:
                                reason = reason_part
                    
                    if fix_text:
                        fixes_applied.append(FixInfo(
                            description=fix_text,
                            reason=reason,
                            line_number=line_num
                        ))
        
        # Extract confidence
        if "CONFIDENCE:" in ai_output.upper():
            conf_section = ai_output.upper().split("CONFIDENCE:")[1][:50].lower()
            if "high" in conf_section:
                confidence = "high"
            elif "low" in conf_section:
                confidence = "low"
            else:
                confidence = "medium"
        
        return fixed_code, bugs_found, fixes_applied, confidence
    
    def _verify_fix(self, fixed_code: str, test_code: str) -> VerificationResult:
        """
        Verify the fix by re-running tests.
        
        Args:
            fixed_code: The fixed source code
            test_code: The test code
            
        Returns:
            VerificationResult with test outcomes
        """
        try:
            from ..runner import run_tests
            
            result = run_tests(fixed_code, test_code)
            
            return VerificationResult(
                ran=True,
                passed=result.success,
                tests_total=result.total,
                tests_passed=result.passed,
                tests_failed=result.failed,
                error_message=result.error_message
            )
            
        except Exception as e:
            return VerificationResult(
                ran=False,
                passed=False,
                error_message=f"Verification failed: {str(e)}"
            )


def fix_code(
    source_code: str,
    test_code: str,
    test_output: str | None = None,
    verify: bool = True,
    api_key: str | None = None
) -> FixResult:
    """
    Main entry point - fix buggy code based on test failures.
    
    Args:
        source_code: The buggy Python source code
        test_code: The pytest test code
        test_output: Raw pytest output (optional - will run tests if not provided)
        verify: Whether to verify the fix by re-running tests (default: True)
        api_key: OpenAI API key (optional - uses env var if not provided)
        
    Returns:
        FixResult with fixed code, bugs found, and verification
        
    Example:
        >>> source = '''
        ... def add(a, b):
        ...     return a - b  # Bug: should be +
        ... '''
        >>> tests = '''
        ... def test_add():
        ...     assert add(2, 3) == 5
        ... '''
        >>> result = fix_code(source, tests)
        >>> print(result.fixed_code)
        def add(a, b):
            return a + b
    """
    fixer = CodeFixer(api_key=api_key)
    return fixer.fix(source_code, test_code, test_output, verify)


def create_fixer(api_key: str | None = None) -> CodeFixer:
    """Factory function to create a CodeFixer instance."""
    return CodeFixer(api_key=api_key)