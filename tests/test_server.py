"""Tests for the pytest-pipeline-mcp server."""

import pytest


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