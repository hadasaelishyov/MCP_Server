"""AI test enhancer that improves template-generated pytest cases using OpenAI."""

import os
from dataclasses import dataclass

from openai import OpenAI

from .base import GeneratedTestCase


@dataclass
class EnhancementResult:
    """Result of AI enhancement."""
    enhanced_tests: list[GeneratedTestCase]
    ai_suggestions: list[str]  # Additional test ideas
    success: bool
    error: str | None = None


class AIEnhancer:
    """Enhance template-generated tests (stronger assertions + extra edge cases)."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        """Initialize enhancer (api_key arg or OPENAI_API_KEY env; model is configurable)."""

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if AI enhancement is available."""
        return self.client is not None

    def enhance_tests(
        self,
        source_code: str,
        test_cases: list[GeneratedTestCase]
    ) -> EnhancementResult:
        """Enhance existing test cases for the given source code (fallbacks on failure)."""

        if not self.is_available():
            return EnhancementResult(
                enhanced_tests=test_cases,
                ai_suggestions=[],
                success=False,
                error="OpenAI API key not configured"
            )

        try:
            # Build the prompt
            prompt = self._build_enhancement_prompt(source_code, test_cases)

            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )

            # Parse response
            ai_output = response.choices[0].message.content
            enhanced_tests, suggestions = self._parse_ai_response(ai_output, test_cases)

            return EnhancementResult(
                enhanced_tests=enhanced_tests,
                ai_suggestions=suggestions,
                success=True
            )

        except Exception as e:
            # On any error, return original tests (fallback)
            return EnhancementResult(
                enhanced_tests=test_cases,
                ai_suggestions=[],
                success=False,
                error=str(e)
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI."""
        return """You are a Python testing expert. Your job is to enhance pytest test cases.

You will receive:
1. Python source code
2. Basic test cases with weak assertions

Your task:
1. Analyze the source code to understand the logic
2. Replace weak assertions (like "assert result is not None") with real expected values
3. Fix exception test trigger conditions
4. ADD 2-3 additional test functions for important edge cases not covered

Rules:
- Keep existing test names and structure
- Improve assertions and input values
- ADD new test functions for missing edge cases (name them test_<function>_edge_<description>)
- Be precise - don't guess if you're not sure
- Return valid Python code

Output format:
```python
# Enhanced tests here (including NEW tests)
```

SUGGESTIONS:
- Any additional ideas not implemented above
"""

    def _build_enhancement_prompt(
        self,
        source_code: str,
        test_cases: list[GeneratedTestCase]
    ) -> str:
        """Build the prompt for AI enhancement."""

        # Convert test cases to code string
        tests_code = self._tests_to_code(test_cases)

        prompt = f"""## Source Code to Test:
```python
{source_code}
```

## Current Tests (need enhancement):
```python
{tests_code}
```

Please enhance these tests:
1. Replace weak assertions with real expected values
2. Fix any "# TODO" or "# May need adjustment" comments
3. Make sure exception tests actually trigger the exception
4. Keep test names and structure the same
"""
        return prompt

    def _tests_to_code(self, test_cases: list[GeneratedTestCase]) -> str:
        """Convert test cases to Python code string."""
        lines = []
        for test in test_cases:
            lines.append(f"def {test.name}():")
            lines.append(f'    """{test.description}"""')
            for body_line in test.body:
                lines.append(f"    {body_line}")
            lines.append("")
        return "\n".join(lines)

    def _parse_ai_response(
        self,
        ai_output: str,
        original_tests: list[GeneratedTestCase]
    ) -> tuple[list[GeneratedTestCase], list[str]]:
        """Parse AI response and extract enhanced tests."""
        
        enhanced_tests = []
        suggestions = []

        # Extract code block
        code_block = self._extract_code_block(ai_output)

        # Extract suggestions
        if "SUGGESTIONS:" in ai_output:
            suggestions_text = ai_output.split("SUGGESTIONS:")[-1]
            for line in suggestions_text.strip().split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    suggestions.append(line[1:].strip())

        # Parse the enhanced test code
        if code_block:
            enhanced_tests = self._parse_test_code(code_block, original_tests)

        # Fallback to original if parsing failed
        if not enhanced_tests:
            enhanced_tests = original_tests

        return enhanced_tests, suggestions

    def _extract_code_block(self, text: str) -> str | None:
        """Extract Python code block from AI response."""
        if "```python" in text:
            start = text.find("```python") + len("```python")
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + len("```")
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        return None

    def _parse_test_code(
        self,
        code: str,
        original_tests: list[GeneratedTestCase]
    ) -> list[GeneratedTestCase]:
        """Parse enhanced test code back into GeneratedTestCase objects."""
        import ast

        enhanced_tests = []
        original_names = {t.name for t in original_tests}

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return original_tests

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                # Find matching original test (if exists)
                original = None
                for t in original_tests:
                    if t.name == node.name:
                        original = t
                        break

                # Extract body lines
                body_lines = []
                for stmt in node.body:
                    # Skip docstring
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        continue
                    try:
                        line = ast.unparse(stmt)
                        body_lines.append(line)
                    except Exception:
                        continue

                # Determine if this is a new test or enhanced existing
                if node.name in original_names:
                    evidence_source = "ai_enhanced"
                    description = original.description if original else f"Test {node.name}"
                else:
                    evidence_source = "ai_generated"
                    description = "AI-generated edge case test."

                enhanced_tests.append(GeneratedTestCase(
                    name=node.name,
                    description=description,
                    body=body_lines,
                    evidence_source=evidence_source
                ))

        return enhanced_tests if enhanced_tests else original_tests


def create_enhancer(api_key: str | None = None) -> AIEnhancer:
    """Factory function to create an AI enhancer."""
    return AIEnhancer(api_key=api_key)
