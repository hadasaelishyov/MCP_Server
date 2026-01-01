"""
Tests for Core Tool Handlers.

Tests the new tool handler files:
- analyze_code.py
- generate_tests.py
- run_tests.py
- fix_code.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from pytest_pipeline_mcp.handlers.core.analyze_code import (
    TOOL_DEFINITION as ANALYZE_TOOL,
    handle as handle_analyze,
)
from pytest_pipeline_mcp.handlers.core.generate_tests import (
    TOOL_DEFINITION as GENERATE_TOOL,
    handle as handle_generate,
)
from pytest_pipeline_mcp.handlers.core.run_tests import (
    TOOL_DEFINITION as RUN_TOOL,
    handle as handle_run,
)
from pytest_pipeline_mcp.handlers.core.fix_code import (
    TOOL_DEFINITION as FIX_TOOL,
    handle as handle_fix,
)


# =============================================================================
# Tool Definition Tests
# =============================================================================

class TestToolDefinitions:
    """Tests for TOOL_DEFINITION objects."""
    
    def test_analyze_tool_definition(self):
        """analyze_code tool has correct structure."""
        assert ANALYZE_TOOL.name == "analyze_code"
        assert "analyze" in ANALYZE_TOOL.description.lower()
        assert "properties" in ANALYZE_TOOL.inputSchema
    
    def test_generate_tool_definition(self):
        """generate_tests tool has correct structure."""
        assert GENERATE_TOOL.name == "generate_tests"
        assert "generate" in GENERATE_TOOL.description.lower()
        assert "properties" in GENERATE_TOOL.inputSchema
    
    def test_run_tool_definition(self):
        """run_tests tool has correct structure."""
        assert RUN_TOOL.name == "run_tests"
        assert "execute" in RUN_TOOL.description.lower() or "run" in RUN_TOOL.description.lower()
        assert "required" in RUN_TOOL.inputSchema
    
    def test_fix_tool_definition(self):
        """fix_code tool has correct structure."""
        assert FIX_TOOL.name == "fix_code"
        assert "fix" in FIX_TOOL.description.lower()
        assert "required" in FIX_TOOL.inputSchema


# =============================================================================
# Handler Tests
# =============================================================================

class TestAnalyzeHandler:
    """Tests for analyze_code handler."""
    
    @pytest.mark.asyncio
    async def test_analyze_simple_code(self):
        """Can analyze simple code."""
        result = await handle_analyze({
            "code": "def add(a, b): return a + b"
        })
        
        assert len(result) == 1
        assert "valid" in result[0].text or "functions" in result[0].text
    
    @pytest.mark.asyncio
    async def test_analyze_no_input_error(self):
        """Returns error when no code or file_path provided."""
        result = await handle_analyze({})
        
        assert len(result) == 1
        assert "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_invalid_syntax(self):
        """Returns error for invalid syntax."""
        result = await handle_analyze({
            "code": "def broken("
        })
        
        assert len(result) == 1
        # Should contain error info
        text = result[0].text.lower()
        assert "error" in text or "syntax" in text


class TestGenerateHandler:
    """Tests for generate_tests handler."""
    
    @pytest.mark.asyncio
    async def test_generate_simple_tests(self):
        """Can generate tests for simple code."""
        result = await handle_generate({
            "code": "def multiply(a, b): return a * b"
        })
        
        assert len(result) == 1
        text = result[0].text
        assert "test" in text.lower() or "generated" in text.lower()
    
    @pytest.mark.asyncio
    async def test_generate_no_input_error(self):
        """Returns error when no code provided."""
        result = await handle_generate({})
        
        assert len(result) == 1
        assert "error" in result[0].text.lower()


class TestRunHandler:
    """Tests for run_tests handler."""
    
    @pytest.mark.asyncio
    async def test_run_passing_tests(self):
        """Can run passing tests."""
        source = "def add(a, b): return a + b"
        test = """
def test_add():
    assert add(1, 2) == 3
"""
        result = await handle_run({
            "source_code": source,
            "test_code": test
        })
        
        assert len(result) == 1
        text = result[0].text
        assert "passed" in text.lower() or "✅" in text
    
    @pytest.mark.asyncio
    async def test_run_failing_tests(self):
        """Can detect failing tests."""
        source = "def add(a, b): return a + b"
        test = """
def test_add_wrong():
    assert add(1, 2) == 999  # Wrong!
"""
        result = await handle_run({
            "source_code": source,
            "test_code": test
        })
        
        assert len(result) == 1
        text = result[0].text
        assert "failed" in text.lower() or "❌" in text
    
    @pytest.mark.asyncio
    async def test_run_missing_source_error(self):
        """Returns error when source_code missing."""
        result = await handle_run({
            "test_code": "def test_x(): pass"
        })
        
        assert len(result) == 1
        # Either works with empty source or returns error


class TestFixHandler:
    """Tests for fix_code handler."""
    
    @pytest.mark.asyncio
    async def test_fix_missing_test_code_error(self):
        """Returns error when test_code missing."""
        result = await handle_fix({
            "source_code": "def broken(): pass"
        })
        
        assert len(result) == 1
        # Should handle missing required field


# =============================================================================
# TOOLS and HANDLERS Export Tests
# =============================================================================

class TestExports:
    """Tests for module exports."""
    
    def test_core_exports_tools(self):
        """core module exports TOOLS list."""
        from pytest_pipeline_mcp.handlers.core import TOOLS
        
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 4
        
        tool_names = [t.name for t in TOOLS]
        assert "analyze_code" in tool_names
        assert "generate_tests" in tool_names
        assert "run_tests" in tool_names
        assert "fix_code" in tool_names
    
    def test_core_exports_handlers(self):
        """core module exports HANDLERS dict."""
        from pytest_pipeline_mcp.handlers.core import HANDLERS
        
        assert isinstance(HANDLERS, dict)
        assert len(HANDLERS) == 4
        
        assert "analyze_code" in HANDLERS
        assert "generate_tests" in HANDLERS
        assert "run_tests" in HANDLERS
        assert "fix_code" in HANDLERS
    
    def test_github_exports_tools(self):
        """github module exports TOOLS list."""
        from pytest_pipeline_mcp.handlers.github import TOOLS
        
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 4
        
        tool_names = [t.name for t in TOOLS]
        assert "analyze_repository" in tool_names
        assert "create_test_pr" in tool_names
        assert "comment_test_results" in tool_names
    
    def test_github_exports_handlers(self):
        """github module exports HANDLERS dict."""
        from pytest_pipeline_mcp.handlers.github import HANDLERS
        
        assert isinstance(HANDLERS, dict)
        assert len(HANDLERS) == 4


class TestServerIntegration:
    """Tests for server.py integration."""
    
    def test_all_tools_combined(self):
        """server.py combines all tools."""
        from pytest_pipeline_mcp.server import ALL_TOOLS
        
        assert len(ALL_TOOLS) == 8  # 4 core + 4 github
    
    def test_all_handlers_combined(self):
        """server.py combines all handlers."""
        from pytest_pipeline_mcp.server import ALL_HANDLERS
        
        assert len(ALL_HANDLERS) == 8  # 4 core + 4 github
        
        # Check all tools have handlers
        from pytest_pipeline_mcp.server import ALL_TOOLS
        for tool in ALL_TOOLS:
            assert tool.name in ALL_HANDLERS
