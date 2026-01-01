"""
Pytest Pipeline MCP Server

A Model Context Protocol server that generates pytest tests
using static code analysis and AI enhancement.

Architecture:
------------
This module is THIN. It only handles:
1. MCP protocol setup
2. Tool registration (imports from tools/)
3. Request routing to handlers

All business logic lives in:
- tools/core/     → Core tools (analyze, generate, run, fix)
- tools/github/   → GitHub integration tools
- services/       → Shared business logic
"""

from __future__ import annotations

import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from .handlers.core import HANDLERS as CORE_HANDLERS

# Import tools and handlers from both modules
from .handlers.core import TOOLS as CORE_TOOLS
from .handlers.github import HANDLERS as GITHUB_HANDLERS
from .handlers.github import TOOLS as GITHUB_TOOLS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
server = Server("pytest-pipeline")


# =============================================================================
# Tool Registration
# =============================================================================

# Combine all tools
ALL_TOOLS = [*CORE_TOOLS, *GITHUB_TOOLS]

# Combine all handlers
ALL_HANDLERS = {**CORE_HANDLERS, **GITHUB_HANDLERS}


@server.list_tools()
async def list_tools():
    """List all available tools."""
    return ALL_TOOLS


# =============================================================================
# Tool Router
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to appropriate handlers."""
    logger.info(f"Tool called: {name}")

    handler = ALL_HANDLERS.get(name)

    if handler:
        return await handler(arguments)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# Entry Point
# =============================================================================

async def run_server():
    """Run the MCP server."""
    logger.info("Starting Pytest Pipeline MCP Server...")
    logger.info(f"Registered {len(ALL_TOOLS)} tools: {[t.name for t in ALL_TOOLS]}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
