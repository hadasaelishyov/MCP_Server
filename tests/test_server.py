"""Tests for the pytest-pipeline-mcp server.

Covers:
- Server creation and configuration
- Tool registration
- Tool routing
- Handler integration
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestServerBasics:
    """Basic server tests."""

    def test_version(self):
        """Test version is defined."""
        from pytest_pipeline_mcp import __version__
        assert __version__ == "0.1.0"

    def test_server_creation(self):
        """Test server can be created."""
        from pytest_pipeline_mcp.server import server
        assert server.name == "pytest-pipeline"


class TestToolRegistration:
    """Test that all tools are properly registered."""

    def test_all_tools_loaded(self):
        """Test all expected tools are in ALL_TOOLS."""
        from pytest_pipeline_mcp.server import ALL_TOOLS
        
        tool_names = [t.name for t in ALL_TOOLS]
        
        # Core tools
        assert "analyze_code" in tool_names
        assert "generate_tests" in tool_names
        assert "run_tests" in tool_names
        assert "fix_code" in tool_names
        
        # GitHub tools
        assert "analyze_repository" in tool_names
        assert "get_repo_file" in tool_names
        assert "create_test_pr" in tool_names
        assert "comment_test_results" in tool_names

    def test_all_handlers_registered(self):
        """Test all tools have corresponding handlers."""
        from pytest_pipeline_mcp.server import ALL_TOOLS, ALL_HANDLERS
        
        for tool in ALL_TOOLS:
            assert tool.name in ALL_HANDLERS, f"Missing handler for {tool.name}"

    def test_tool_schemas_valid(self):
        """Test all tools have valid input schemas."""
        from pytest_pipeline_mcp.server import ALL_TOOLS
        
        for tool in ALL_TOOLS:
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema


class TestToolRouting:
    """Test tool call routing."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Test that unknown tool names return error message."""
        from pytest_pipeline_mcp.server import call_tool
        
        result = await call_tool("nonexistent_tool", {})
        
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_analyze_code_routing(self):
        """Test analyze_code routes to correct handler."""
        from pytest_pipeline_mcp.server import call_tool
        
        result = await call_tool("analyze_code", {
            "code": "def add(a, b): return a + b"
        })
        
        assert len(result) == 1
        assert '"valid": true' in result[0].text or '"valid":true' in result[0].text

    @pytest.mark.asyncio
    async def test_generate_tests_routing(self):
        """Test generate_tests routes to correct handler."""
        from pytest_pipeline_mcp.server import call_tool
        
        result = await call_tool("generate_tests", {
            "code": "def add(a: int, b: int) -> int:\n    return a + b"
        })
        
        assert len(result) == 1
        # Should contain generated test code
        assert "def test_" in result[0].text or "test" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_run_tests_routing(self):
        """Test run_tests routes to correct handler."""
        from pytest_pipeline_mcp.server import call_tool
        
        source = "def add(a, b): return a + b"
        tests = "from module import add\ndef test_add(): assert add(1, 2) == 3"
        
        result = await call_tool("run_tests", {
            "source_code": source,
            "test_code": tests
        })
        
        assert len(result) == 1
        # Should contain test results
        assert "test" in result[0].text.lower()


class TestHandlerIntegration:
    """Test handlers integrate correctly with services."""

    @pytest.mark.asyncio
    async def test_analyze_empty_code_returns_error(self):
        """Test analyze_code handles empty input gracefully."""
        from pytest_pipeline_mcp.server import call_tool
        
        result = await call_tool("analyze_code", {"code": ""})
        
        assert len(result) == 1
        assert "error" in result[0].text.lower() or "empty" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_analyze_invalid_syntax_returns_error(self):
        """Test analyze_code handles syntax errors gracefully."""
        from pytest_pipeline_mcp.server import call_tool
        
        result = await call_tool("analyze_code", {
            "code": "def broken(: pass"
        })
        
        assert len(result) == 1
        assert "syntax" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fix_code_without_api_key(self):
        """Test fix_code gracefully handles missing API key."""
        from pytest_pipeline_mcp.server import call_tool
        
        with patch.dict('os.environ', {}, clear=True):
            result = await call_tool("fix_code", {
                "source_code": "def add(a, b): return a - b",
                "test_code": "def test(): assert add(1, 2) == 3"
            })
        
        assert len(result) == 1
        # Should mention API key or gracefully fail
        text = result[0].text.lower()
        assert "api" in text or "key" in text or "error" in text


class TestListTools:
    """Test the list_tools endpoint."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all(self):
        """Test list_tools returns all registered tools."""
        from pytest_pipeline_mcp.server import list_tools, ALL_TOOLS
        
        result = await list_tools()
        
        assert len(result) == len(ALL_TOOLS)
        assert result == ALL_TOOLS