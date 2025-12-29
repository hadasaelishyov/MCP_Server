"""
Comment Test Results Tool - Post test results as a comment on a GitHub PR.

This tool:
1. Formats test results as markdown
2. Posts the comment on the specified PR

Uses GitHubService for posting comments.
"""

from __future__ import annotations

from mcp.types import Tool, TextContent

from ...services import GitHubService


# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="comment_test_results",
    description=(
        "Add test results as a comment on a GitHub Pull Request. "
        "Posts formatted results with pass/fail status and optional coverage report."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "GitHub repository URL"
            },
            "pr_number": {
                "type": "integer",
                "description": "Pull request number to comment on"
            },
            "test_results": {
                "type": "string",
                "description": "Test execution results to post"
            },
            "coverage_report": {
                "type": "string",
                "description": "Optional coverage report to include"
            }
        },
        "required": ["repo_url", "pr_number", "test_results"]
    }
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """
    Handle comment_test_results tool call.
    
    Args:
        arguments: Tool arguments
        
    Returns:
        List with single TextContent containing result
    """
    repo_url = arguments.get("repo_url", "")
    pr_number = arguments.get("pr_number", 0)
    test_results = arguments.get("test_results", "")
    coverage_report = arguments.get("coverage_report")
    
    # Validate required inputs
    if not repo_url:
        return [TextContent(type="text", text="Error: repo_url is required")]
    if not pr_number:
        return [TextContent(type="text", text="Error: pr_number is required")]
    if not test_results:
        return [TextContent(type="text", text="Error: test_results is required")]
    
    # Create service
    github_service = GitHubService()
    
    # Check for token
    if not github_service.has_token:
        return [TextContent(
            type="text",
            text="Error: GitHub token required to post comments. Set GITHUB_TOKEN environment variable."
        )]
    
    # Format the comment
    comment_body = format_test_comment(test_results, coverage_report)
    
    # Post comment
    result = github_service.post_comment(
        repo_url=repo_url,
        pr_number=pr_number,
        body=comment_body
    )
    
    if not result.success:
        return [TextContent(
            type="text",
            text=f"Error: {result.error.message}"
        )]
    
    comment_info = result.data
    
    # Format success response
    response = f"""💬 COMMENT POSTED
==================================================

✅ Test results posted to PR successfully!

🔗 Comment URL: {comment_info.url}
📌 PR Number: #{pr_number}
"""
    
    return [TextContent(type="text", text=response)]


# =============================================================================
# Helper Functions
# =============================================================================

def format_test_comment(test_results: str, coverage_report: str | None) -> str:
    """
    Format test results as a nice markdown comment.
    
    Args:
        test_results: Raw test results string
        coverage_report: Optional coverage report
        
    Returns:
        Formatted markdown comment
    """
    # Determine status from results
    results_lower = test_results.lower()
    
    is_success = (
        ("passed" in results_lower and "failed" not in results_lower) or
        "0 failed" in results_lower or
        "failed: 0" in results_lower or
        "all tests passed" in results_lower
    )
    
    # Check for partial success
    has_failures = (
        "failed" in results_lower and 
        "0 failed" not in results_lower and
        "failed: 0" not in results_lower
    )
    
    if is_success:
        status_emoji = "✅"
        status_text = "All tests passed!"
    elif has_failures:
        status_emoji = "❌"
        status_text = "Some tests failed"
    else:
        status_emoji = "⚠️"
        status_text = "Test results"
    
    # Build comment
    lines = [
        f"## {status_emoji} Test Results",
        "",
        f"**Status:** {status_text}",
        "",
        "### Details",
        "```",
        test_results,
        "```",
    ]
    
    # Add coverage if provided
    if coverage_report:
        lines.extend([
            "",
            "### 📊 Coverage Report",
            "```",
            coverage_report,
            "```",
        ])
    
    # Footer
    lines.extend([
        "",
        "---",
        "*Generated by [pytest-generator-mcp](https://github.com/yourusername/pytest-generator-mcp)* 🤖"
    ])
    
    return "\n".join(lines)
