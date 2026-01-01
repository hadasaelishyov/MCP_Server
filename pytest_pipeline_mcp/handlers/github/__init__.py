"""Registry for GitHub MCP tool definitions and handlers."""

from .analyze_repository import (
    TOOL_DEFINITION as ANALYZE_REPOSITORY_TOOL,
)
from .analyze_repository import (
    handle as handle_analyze_repository,
)
from .comment_test_results import (
    TOOL_DEFINITION as COMMENT_TEST_RESULTS_TOOL,
)
from .comment_test_results import (
    handle as handle_comment_test_results,
)
from .get_repo_file import (
    TOOL_DEFINITION as GET_REPO_FILE_TOOL,
)
from .get_repo_file import (
    handle as handle_get_repo_file,
)
from .create_test_pr import (
    TOOL_DEFINITION as CREATE_TEST_PR_TOOL,
)
from .create_test_pr import (
    handle as handle_create_test_pr,
)

# All GitHub tool definitions
TOOLS = [
    ANALYZE_REPOSITORY_TOOL,
    GET_REPO_FILE_TOOL,
    CREATE_TEST_PR_TOOL,
    COMMENT_TEST_RESULTS_TOOL,
]

# Tool name to handler mapping
HANDLERS = {
    "analyze_repository": handle_analyze_repository,
    "get_repo_file": handle_get_repo_file,
    "create_test_pr": handle_create_test_pr,
    "comment_test_results": handle_comment_test_results,
}


__all__ = [
    # Tool definitions
    "TOOLS",
    "ANALYZE_REPOSITORY_TOOL",
    "GET_REPO_FILE_TOOL",
    "CREATE_TEST_PR_TOOL",
    "COMMENT_TEST_RESULTS_TOOL",
    # Handlers
    "HANDLERS",
    "handle_analyze_repository",
    "handle_get_repo_file",
    "handle_create_test_pr",
    "handle_comment_test_results",
]
