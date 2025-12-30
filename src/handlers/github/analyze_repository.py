"""
Analyze Repository Tool - Clone and analyze a GitHub repository.

This tool:
1. Clones the repository to a temp directory
2. Finds all Python files
3. Analyzes each file using AnalysisService
4. Returns a summary of what needs tests

Uses GitHubService for cloning, AnalysisService for analysis.
"""

from __future__ import annotations

from mcp.types import TextContent, Tool

from ...core.repository.models import RepositoryAnalysis
from ...services import RepositoryAnalysisService

# =============================================================================
# Tool Definition
# =============================================================================

TOOL_DEFINITION = Tool(
    name="analyze_repository",
    description=(
        "Clone and analyze a GitHub repository. "
        "Returns analysis for all Python files including: function/class counts, "
        "complexity metrics, type hint coverage, and identifies which files need tests."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "GitHub repository URL (e.g., https://github.com/user/repo)"
            },
            "branch": {
                "type": "string",
                "description": "Branch name to analyze (default: main)"
            },
            "path_filter": {
                "type": "string",
                "description": "Only analyze files matching pattern (e.g., 'src/**/*.py')"
            }
        },
        "required": ["repo_url"]
    }
)


# =============================================================================
# Handler
# =============================================================================

async def handle(arguments: dict) -> list[TextContent]:
    """
    Handle analyze_repository tool call.
    
    Args:
        arguments: Tool arguments (repo_url, branch, path_filter)
        
    Returns:
        List with single TextContent containing analysis results
    """
    repo_url = arguments.get("repo_url", "")
    branch = arguments.get("branch", "main")
    path_filter = arguments.get("path_filter")

    # Validate input
    if not repo_url:
        return [TextContent(
            type="text",
            text="Error: repo_url is required"
        )]

    # Analyze repository
    service = RepositoryAnalysisService()
    result = service.analyze_repository(repo_url, branch, path_filter)

    if not result.success:
        return [TextContent(
            type="text",
            text=f"Error: {result.error.message}"
        )]

    # Format response
    return [TextContent(
        type="text",
        text=format_analysis(result.data)
    )]


# =============================================================================
# Response Formatting
# =============================================================================

def format_analysis(analysis: RepositoryAnalysis) -> str:
    """Format repository analysis as readable text."""
    lines = [
        "📦 REPOSITORY ANALYSIS",
        "=" * 50,
        "",
        f"Repository: {analysis.repo_url}",
        f"Branch: {analysis.branch}",
        "",
        "📊 Summary:",
        f"  • Total Python files: {analysis.total_files}",
        f"  • Files needing tests: {analysis.files_needing_tests}",
        f"  • Total functions: {analysis.total_functions}",
        f"  • Total classes: {analysis.total_classes}",
        "",
    ]

    # Files needing tests
    files_need_tests = [f for f in analysis.files if f.needs_tests]
    if files_need_tests:
        lines.append("🔴 Files needing tests:")
        for f in files_need_tests:
            lines.append(f"  • {f.relative_path}")
            lines.append(f"    Functions: {f.functions_count}, Classes: {f.classes_count}, Complexity: {f.complexity:.1f}")
        lines.append("")

    # Test files found
    test_files = [f for f in analysis.files if f.is_test_file]
    if test_files:
        lines.append("✅ Test files found:")
        for f in test_files:
            lines.append(f"  • {f.relative_path}")
        lines.append("")

    # All files overview
    lines.append("📋 All Python files:")
    for f in analysis.files:
        if f.needs_tests:
            status = "🔴"  # Needs tests
        elif f.is_test_file:
            status = "✅"  # Is a test file
        else:
            status = "⚪"  # Empty or no testable code

        lines.append(f"  {status} {f.relative_path}")

        # Show warnings if any
        for warning in f.warnings[:2]:
            lines.append(f"      ⚠️ {warning}")

    return "\n".join(lines)
