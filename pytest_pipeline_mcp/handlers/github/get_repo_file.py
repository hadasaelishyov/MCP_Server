"""MCP handler for get_repo_file (delegates to GitHubService)."""

from __future__ import annotations
from typing import Final

from mcp.types import TextContent, Tool

from ...services import GitHubService

MAX_CODE_SIZE: Final[int] = 1_000_000  # 1MB

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="get_repo_file",
    description=(
        "Fetch a file content from a GitHub repository (by path + branch/ref). "
        "Useful to feed code into other tools (e.g., generate_tests) without manual copy/paste."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "GitHub repository URL (e.g., https://github.com/user/repo)"
            },
            "file_path": {
                "type": "string",
                "description": "Path to file in repository (e.g., 'src/app.py')"
            },
            "branch": {
                "type": "string",
                "description": "Branch/ref to fetch from (default: main)"
            },
            "format": {
                "type": "string",
                "description": "Output format: 'raw' (default) or 'markdown'",
                "enum": ["raw", "markdown"]
            }
        },
        "required": ["repo_url", "file_path"]
    }
)

# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """Fetch a file from a GitHub repo and return it as raw text or markdown."""

    repo_url = arguments.get("repo_url", "")
    file_path = arguments.get("file_path", "")
    branch = arguments.get("branch", "main")
    output_format = arguments.get("format", "raw")

    # Validate required inputs
    if not repo_url:
        return [TextContent(type="text", text="Error: repo_url is required")]
    if not file_path:
        return [TextContent(type="text", text="Error: file_path is required")]
    if output_format not in ("raw", "markdown"):
        return [TextContent(type="text", text="Error: format must be 'raw' or 'markdown'")]

    github_service = GitHubService()
    result = github_service.get_file_content(
        repo_url=repo_url,
        file_path=file_path,
        branch=branch
    )

    if not result.success:
        return [TextContent(type="text", text=f"Error: {result.error.message}")]

    code = result.data or ""

    # Size guard (keep consistent with project limits)
    try:
        size_bytes = len(code.encode("utf-8"))
    except Exception:
        size_bytes = len(code)
        
    # Guardrail: avoid returning huge files via MCP (token/latency blowups and client limits).
    if size_bytes > MAX_CODE_SIZE:
        return [TextContent(
            type="text",
            text=(
                f"Error: File too large ({size_bytes} bytes). "
                f"Limit is {MAX_CODE_SIZE} bytes."
            )
        )]
        
    # Markdown output wraps the file in a code fence to preserve formatting in the client UI.
    if output_format == "markdown":
        text = f"### {file_path} ({branch})\n\n```python\n{code}\n```"
    else:
        text = code

    return [TextContent(type="text", text=text)]
