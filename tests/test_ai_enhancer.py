"""Tests for AI Enhancer module."""

import pytest
from unittest.mock import Mock, patch
import os

from src.tools.core.generators.ai_enhancer import AIEnhancer, EnhancementResult, create_enhancer
from src.tools.core.generators.base import GeneratedTestCase


class TestAIEnhancerInit:
    """Test AIEnhancer initialization."""
    
    def test_create_without_api_key(self):
        """Test enhancer creation without API key."""
        # Temporarily remove env var if set
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            enhancer = AIEnhancer(api_key=None)
            assert enhancer.is_available() is False
        finally:
            # Restore env var if it existed
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    def test_create_with_api_key(self):
        """Test enhancer creation with API key."""
        enhancer = AIEnhancer(api_key="test-key")
        assert enhancer.is_available() is True
    
    def test_create_enhancer_factory(self):
        """Test factory function."""
        enhancer = create_enhancer(api_key="test-key")
        assert isinstance(enhancer, AIEnhancer)
        assert enhancer.is_available() is True
    
    def test_default_model(self):
        """Test default model is set."""
        enhancer = AIEnhancer(api_key="test-key")
        assert enhancer.model == "gpt-4o-mini"
    
    def test_custom_model(self):
        """Test custom model can be set."""
        enhancer = AIEnhancer(api_key="test-key", model="gpt-4")
        assert enhancer.model == "gpt-4"


class TestAIEnhancerPrompts:
    """Test prompt building."""
    
    def test_build_enhancement_prompt(self):
        """Test prompt contains source code and tests."""
        enhancer = AIEnhancer(api_key="test-key")
        
        source_code = "def add(a, b): return a + b"
        test_cases = [
            GeneratedTestCase(
                name="test_add_basic",
                description="Test add function.",
                body=["result = add(0, 0)", "assert result is not None"],
                evidence_source="template"
            )
        ]
        
        prompt = enhancer._build_enhancement_prompt(source_code, test_cases)
        
        assert "def add(a, b): return a + b" in prompt
        assert "test_add_basic" in prompt
        assert "assert result is not None" in prompt
    
    def test_system_prompt_content(self):
        """Test system prompt has key instructions."""
        enhancer = AIEnhancer(api_key="test-key")
        system_prompt = enhancer._get_system_prompt()
        
        assert "Python" in system_prompt
        assert "pytest" in system_prompt
        assert "assertion" in system_prompt.lower()


class TestAIEnhancerParsing:
    """Test response parsing."""
    
    def test_extract_code_block_python(self):
        """Test extracting Python code block."""
        enhancer = AIEnhancer(api_key="test-key")
        
        text = '''Here is the enhanced code:
````python
def test_add():
    assert add(1, 2) == 3
````
That should work!'''
        
        result = enhancer._extract_code_block(text)
        assert "def test_add():" in result
        assert "assert add(1, 2) == 3" in result
    
    def test_extract_code_block_generic(self):
        """Test extracting generic code block."""
        enhancer = AIEnhancer(api_key="test-key")
        
        text = '''```
def test_something():
    pass
````'''
        
        result = enhancer._extract_code_block(text)
        assert "def test_something():" in result
    
    def test_extract_code_block_none(self):
        """Test returns None when no code block."""
        enhancer = AIEnhancer(api_key="test-key")
        
        text = "No code block here!"
        result = enhancer._extract_code_block(text)
        assert result is None
    
    def test_tests_to_code(self):
        """Test converting test cases to code string."""
        enhancer = AIEnhancer(api_key="test-key")
        
        test_cases = [
            GeneratedTestCase(
                name="test_example",
                description="Example test.",
                body=["x = 1", "assert x == 1"],
                evidence_source="template"
            )
        ]
        
        code = enhancer._tests_to_code(test_cases)
        
        assert "def test_example():" in code
        assert "Example test." in code
        assert "x = 1" in code
        assert "assert x == 1" in code


class TestAIEnhancerFallback:
    """Test fallback behavior."""
    
    def test_fallback_when_no_api_key(self):
        """Test returns original tests when no API key."""
        # Temporarily remove env var if set
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            enhancer = AIEnhancer(api_key=None)
            
            original_tests = [
                GeneratedTestCase(
                    name="test_original",
                    description="Original test.",
                    body=["assert True"],
                    evidence_source="template"
                )
            ]
            
            result = enhancer.enhance_tests("def foo(): pass", original_tests)
            
            assert result.success is False
            assert "API key" in result.error
            assert result.enhanced_tests == original_tests
        finally:
            # Restore env var if it existed
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    @patch("src.tools.core.generators.ai_enhancer.OpenAI")
    def test_fallback_on_api_error(self, mock_openai_class):
        """Test returns original tests on API error."""
        # Setup mock to raise an error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        enhancer = AIEnhancer(api_key="test-key")
        
        original_tests = [
            GeneratedTestCase(
                name="test_original",
                description="Original test.",
                body=["assert True"],
                evidence_source="template"
            )
        ]
        
        result = enhancer.enhance_tests("def foo(): pass", original_tests)
        
        assert result.success is False
        assert "API Error" in result.error
        assert result.enhanced_tests == original_tests


class TestAIEnhancerIntegration:
    """Integration tests with mocked API."""
    
    @patch("src.tools.core.generators.ai_enhancer.OpenAI")
    def test_successful_enhancement(self, mock_openai_class):
        """Test successful AI enhancement."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
```python
def test_add_basic():
    """Test add function."""
    assert add(2, 3) == 5
```

SUGGESTIONS:
- Test with negative numbers
- Test with zero
'''
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        enhancer = AIEnhancer(api_key="test-key")
        
        original_tests = [
            GeneratedTestCase(
                name="test_add_basic",
                description="Test add function.",
                body=["result = add(0, 0)", "assert result is not None"],
                evidence_source="template"
            )
        ]
        
        result = enhancer.enhance_tests(
            "def add(a, b): return a + b",
            original_tests
        )
        
        assert result.success is True
        assert result.error is None
        assert len(result.enhanced_tests) > 0
        assert len(result.ai_suggestions) >= 1
    
    @patch("src.tools.core.generators.ai_enhancer.OpenAI")
    def test_enhancement_preserves_test_count(self, mock_openai_class):
        """Test that enhancement keeps all tests."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
```python
def test_one():
    """Test one."""
    assert 1 == 1

def test_two():
    """Test two."""
    assert 2 == 2
```
'''
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        enhancer = AIEnhancer(api_key="test-key")
        
        original_tests = [
            GeneratedTestCase(
                name="test_one",
                description="Test one.",
                body=["assert True"],
                evidence_source="template"
            ),
            GeneratedTestCase(
                name="test_two",
                description="Test two.",
                body=["assert True"],
                evidence_source="template"
            )
        ]
        
        result = enhancer.enhance_tests("def foo(): pass", original_tests)
        
        assert result.success is True
        assert len(result.enhanced_tests) == 2
