"""Tests for the pytest-generator-mcp server."""

import pytest


class TestServerBasics:
    """Basic server tests."""

    def test_version(self):
        """Test version is defined."""
        from src import __version__
        assert __version__ == "0.1.0"

    def test_server_creation(self):
        """Test server can be created."""
        from src.server import server
        assert server.name == "pytest-generator"