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

from dataclasses import dataclass, field

from mcp.types import TextContent, Tool

from ...services import AnalysisService, GitHubService, ServiceResult

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    relative_path: str
    functions_count: int
    classes_count: int
    is_test_file: bool
    complexity: float
    type_hint_coverage: float
    warnings: list[str] = field(default_factory=list)

    @property
    def needs_tests(self) -> bool:
        """Check if this file needs tests."""
        return (
            not self.is_test_file
            and (self.functions_count > 0 or self.classes_count > 0)
        )


@dataclass
class RepositoryAnalysis:
    """Complete analysis of a repository."""
    repo_url: str
    branch: str
    files: list[FileAnalysis]

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def files_needing_tests(self) -> int:
        return sum(1 for f in self.files if f.needs_tests)

    @property
    def total_functions(self) -> int:
        return sum(f.functions_count for f in self.files)

    @property
    def total_classes(self) -> int:
        return sum(f.classes_count for f in self.files)


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
    result = analyze_repository(repo_url, branch, path_filter)

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
# Business Logic
# =============================================================================

def analyze_repository(
    repo_url: str,
    branch: str = "main",
    path_filter: str | None = None
) -> ServiceResult[RepositoryAnalysis]:
    """
    Clone and analyze a GitHub repository.
    
    Args:
        repo_url: GitHub repository URL
        branch: Branch to analyze
        path_filter: Optional glob pattern to filter files
        
    Returns:
        ServiceResult with RepositoryAnalysis
    """
    github_service = GitHubService()
    analysis_service = AnalysisService()

    # Clone repository
    clone_result = github_service.clone_repository(repo_url, branch)

    if not clone_result.success:
        return ServiceResult.fail(
            clone_result.error.code,
            clone_result.error.message
        )

    clone_info = clone_result.data
    repo_path = clone_info.path
    actual_branch = clone_info.branch

    try:
        # Find Python files
        if path_filter:
            py_files = list(repo_path.glob(path_filter))
        else:
            py_files = list(repo_path.rglob("*.py"))

        # Filter out hidden directories, __pycache__, venv, etc.
        py_files = [
            f for f in py_files
            if not any(
                part.startswith('.') or
                part in ('__pycache__', 'venv', '.venv', 'node_modules', 'dist', 'build')
                for part in f.parts
            )
        ]

        # Analyze each file
        files_analyzed: list[FileAnalysis] = []

        for py_file in py_files:
            relative_path = str(py_file.relative_to(repo_path))

            # Check if it's a test file
            is_test_file = (
                "test" in py_file.name.lower() or
                py_file.name.startswith("test_") or
                "/tests/" in relative_path or
                "\\tests\\" in relative_path
            )

            # Analyze the file
            result = analysis_service.analyze(file_path=str(py_file))

            if result.success:
                analysis = result.data
                file_analysis = FileAnalysis(
                    relative_path=relative_path,
                    functions_count=analysis.total_functions,
                    classes_count=analysis.total_classes,
                    is_test_file=is_test_file,
                    complexity=analysis.average_complexity,
                    type_hint_coverage=analysis.type_hint_coverage,
                    warnings=analysis.warnings[:3]  # Limit warnings
                )
            else:
                # File had errors, still include it with zero counts
                file_analysis = FileAnalysis(
                    relative_path=relative_path,
                    functions_count=0,
                    classes_count=0,
                    is_test_file=is_test_file,
                    complexity=0,
                    type_hint_coverage=0,
                    warnings=[f"Parse error: {result.error.message}"]
                )

            files_analyzed.append(file_analysis)

        return ServiceResult.ok(RepositoryAnalysis(
            repo_url=repo_url,
            branch=actual_branch,
            files=files_analyzed
        ))

    finally:
        # Always cleanup
        github_service.cleanup_clone(repo_path)


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
