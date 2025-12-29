"""
GitHub Integration Tools

Tools for integrating with GitHub repositories:
- analyze_repository: Clone and analyze a repo, find files needing tests
- create_test_pr: Create a PR with generated tests
- comment_test_results: Post test results as PR comment

Usage:
    from src.tools.github import TOOLS, HANDLERS
    
    # Get all tool definitions
    for tool in TOOLS:
        print(tool.name)
    
    # Get handler for a tool
    handler = HANDLERS.get("analyze_repository")
    result = await handler({"repo_url": "..."})
"""

from .analyze_repository import (
    TOOL_DEFINITION as ANALYZE_REPOSITORY_TOOL,
    handle as handle_analyze_repository,
)

from .create_test_pr import (
    TOOL_DEFINITION as CREATE_TEST_PR_TOOL,
    handle as handle_create_test_pr,
)

from .comment_test_results import (
    TOOL_DEFINITION as COMMENT_TEST_RESULTS_TOOL,
    handle as handle_comment_test_results,
)


# All GitHub tool definitions
TOOLS = [
    ANALYZE_REPOSITORY_TOOL,
    CREATE_TEST_PR_TOOL,
    COMMENT_TEST_RESULTS_TOOL,
]

# Tool name to handler mapping
HANDLERS = {
    "analyze_repository": handle_analyze_repository,
    "create_test_pr": handle_create_test_pr,
    "comment_test_results": handle_comment_test_results,
}


__all__ = [
    # Tool definitions
    "TOOLS",
    "ANALYZE_REPOSITORY_TOOL",
    "CREATE_TEST_PR_TOOL", 
    "COMMENT_TEST_RESULTS_TOOL",
    # Handlers
    "HANDLERS",
    "handle_analyze_repository",
    "handle_create_test_pr",
    "handle_comment_test_results",
]
