"""
Tests for GitHub Integration Tools.

Tests:
- GitHubService (clone, PR, comment)
- analyze_repository tool
- create_test_pr tool
- comment_test_results tool
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from pytest_pipeline_mcp.services.github import GitHubService, CloneResult, PRInfo, CommentInfo
from pytest_pipeline_mcp.services.base import ErrorCode
from pytest_pipeline_mcp.core.repo_analysis.models import FileAnalysis, RepositoryAnalysis
from pytest_pipeline_mcp.handlers.github.analyze_repository import format_analysis

from pytest_pipeline_mcp.handlers.github.create_test_pr import generate_pr_description
from pytest_pipeline_mcp.handlers.github.comment_test_results import format_test_comment


# =============================================================================
# GitHubService Tests
# =============================================================================

class TestGitHubService:
    """Tests for GitHubService."""
    
    def test_init_without_token(self):
        """Service can initialize without token."""
        import os
        original_token = os.environ.pop("GITHUB_TOKEN", None)
        try:
            service = GitHubService(token=None)
            assert service.has_token is False
        finally:
            if original_token:
                os.environ["GITHUB_TOKEN"] = original_token
    
    def test_init_with_token(self):
        """Service initializes with token."""
        service = GitHubService(token="test_token")
        assert service.has_token is True
    
    def test_parse_https_url(self):
        """Parse standard HTTPS URL."""
        service = GitHubService()
        result = service._parse_repo_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")
    
    def test_parse_https_url_with_git(self):
        """Parse HTTPS URL with .git suffix."""
        service = GitHubService()
        result = service._parse_repo_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")
    
    def test_parse_invalid_url(self):
        """Invalid URL returns None."""
        service = GitHubService()
        result = service._parse_repo_url("not-a-github-url")
        assert result is None
    
    def test_clone_invalid_url(self):
        """Clone with invalid URL returns error."""
        service = GitHubService()
        result = service.clone_repository("invalid-url")
        assert result.success is False
        assert result.error.code == ErrorCode.VALIDATION_ERROR
    
    def test_post_comment_requires_token(self):
        """Posting comment requires token."""
        import os
        original = os.environ.pop("GITHUB_TOKEN", None)
        try:
            service = GitHubService(token=None)
            result = service.post_comment(
                repo_url="https://github.com/test/repo",
                pr_number=1,
                body="Test comment"
            )
            assert result.success is False
            assert result.error.code in [
                ErrorCode.GITHUB_AUTH_ERROR,
                ErrorCode.GITHUB_API_ERROR
            ]
        finally:
            if original:
                os.environ["GITHUB_TOKEN"] = original


# =============================================================================
# FileAnalysis Model Tests
# =============================================================================

class TestFileAnalysis:
    """Tests for FileAnalysis dataclass."""
    
    def test_needs_tests_with_functions(self):
        """File with functions needs tests."""
        analysis = FileAnalysis(
            relative_path="src/calc.py",
            functions_count=3,
            classes_count=0,
            is_test_file=False,
            complexity=2.0,
            type_hint_coverage=80.0
        )
        assert analysis.needs_tests is True
    
    def test_needs_tests_with_classes(self):
        """File with classes needs tests."""
        analysis = FileAnalysis(
            relative_path="src/models.py",
            functions_count=0,
            classes_count=2,
            is_test_file=False,
            complexity=3.0,
            type_hint_coverage=90.0
        )
        assert analysis.needs_tests is True
    
    def test_test_file_does_not_need_tests(self):
        """Test files don't need tests."""
        analysis = FileAnalysis(
            relative_path="tests/test_calc.py",
            functions_count=10,
            classes_count=1,
            is_test_file=True,
            complexity=1.5,
            type_hint_coverage=50.0
        )
        assert analysis.needs_tests is False
    
    def test_empty_file_does_not_need_tests(self):
        """Empty files don't need tests."""
        analysis = FileAnalysis(
            relative_path="src/__init__.py",
            functions_count=0,
            classes_count=0,
            is_test_file=False,
            complexity=0.0,
            type_hint_coverage=0.0
        )
        assert analysis.needs_tests is False


# =============================================================================
# RepositoryAnalysis Model Tests
# =============================================================================

class TestRepositoryAnalysis:
    """Tests for RepositoryAnalysis dataclass."""
    
    def test_total_files(self):
        """Count total files."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="main",
            files=[
                FileAnalysis("a.py", 1, 0, False, 1.0, 80.0),
                FileAnalysis("b.py", 2, 1, False, 2.0, 90.0),
            ]
        )
        assert analysis.total_files == 2
    
    def test_files_needing_tests(self):
        """Count files needing tests."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="main",
            files=[
                FileAnalysis("src/a.py", 1, 0, False, 1.0, 80.0),
                FileAnalysis("tests/test_a.py", 5, 0, True, 1.0, 50.0),
                FileAnalysis("src/__init__.py", 0, 0, False, 0.0, 0.0),
            ]
        )
        assert analysis.files_needing_tests == 1
    
    def test_total_functions(self):
        """Sum functions across files."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="main",
            files=[
                FileAnalysis("a.py", 3, 0, False, 1.0, 80.0),
                FileAnalysis("b.py", 5, 0, False, 2.0, 90.0),
            ]
        )
        assert analysis.total_functions == 8


# =============================================================================
# Response Formatting Tests
# =============================================================================

class TestFormatAnalysis:
    """Tests for format_analysis function."""
    
    def test_includes_repo_url(self):
        """Output includes repo URL."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="main",
            files=[]
        )
        output = format_analysis(analysis)
        assert "https://github.com/test/repo" in output
    
    def test_includes_branch(self):
        """Output includes branch name."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="develop",
            files=[]
        )
        output = format_analysis(analysis)
        assert "develop" in output
    
    def test_shows_files_needing_tests(self):
        """Shows files that need tests."""
        analysis = RepositoryAnalysis(
            repo_url="https://github.com/test/repo",
            branch="main",
            files=[
                FileAnalysis("src/calc.py", 3, 1, False, 2.5, 75.0),
            ]
        )
        output = format_analysis(analysis)
        assert "src/calc.py" in output
        assert "🔴" in output  # Red indicator for needs tests


class TestGeneratePRDescription:
    """Tests for PR description generation."""
    
    def test_includes_target_file(self):
        """Description includes target file."""
        desc = generate_pr_description(
            "src/calculator.py",
            "def test_add(): pass"
        )
        assert "calculator.py" in desc
    
    def test_counts_tests(self):
        """Description counts tests."""
        test_code = """
def test_one(): pass
def test_two(): pass
def test_three(): pass
"""
        desc = generate_pr_description("src/calc.py", test_code)
        assert "3" in desc


class TestFormatTestComment:
    """Tests for test comment formatting."""
    
    def test_passing_tests_show_success(self):
        """Passing tests show success emoji."""
        comment = format_test_comment("5 passed, 0 failed", None)
        assert "✅" in comment
        assert "passed" in comment.lower()
    
    def test_failing_tests_show_failure(self):
        """Failing tests show failure emoji."""
        comment = format_test_comment("3 passed, 2 failed", None)
        assert "❌" in comment
    
    def test_includes_coverage_when_provided(self):
        """Coverage is included when provided."""
        comment = format_test_comment(
            "5 passed",
            "Coverage: 95%"
        )
        assert "Coverage" in comment
        assert "95%" in comment
    
    def test_no_coverage_section_when_none(self):
        """No coverage section when not provided."""
        comment = format_test_comment("5 passed", None)
        assert "Coverage Report" not in comment


# =============================================================================
# Integration Tests (with mocking)
# =============================================================================

class TestAnalyzeRepositoryIntegration:
    """Integration tests for analyze_repository tool."""
    
    @pytest.mark.asyncio
    async def test_missing_repo_url_error(self):
        """Missing repo_url returns error."""
        from pytest_pipeline_mcp.handlers.github.analyze_repository import handle
        
        result = await handle({})
        assert len(result) == 1
        assert "Error" in result[0].text
        assert "repo_url" in result[0].text
class TestGetRepoFileIntegration:
    """Integration tests for get_repo_file tool."""

    @pytest.mark.asyncio
    async def test_missing_repo_url_error(self):
        """Missing repo_url returns error."""
        from pytest_pipeline_mcp.handlers.github.get_repo_file import handle

        result = await handle({"file_path": "src/app.py"})
        assert len(result) == 1
        assert "repo_url" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_file_path_error(self):
        """Missing file_path returns error."""
        from pytest_pipeline_mcp.handlers.github.get_repo_file import handle

        result = await handle({"repo_url": "https://github.com/test/repo"})
        assert len(result) == 1
        assert "file_path" in result[0].text

    @pytest.mark.asyncio
    async def test_success_returns_raw_code(self):
        """Successful call returns raw file content."""
        from pytest_pipeline_mcp.handlers.github.get_repo_file import handle
        from pytest_pipeline_mcp.services.base import ServiceResult

        with patch("pytest_pipeline_mcp.handlers.github.get_repo_file.GitHubService") as mock_cls:
            mock_service = mock_cls.return_value
            mock_service.get_file_content.return_value = ServiceResult.ok("print('hi')\n")

            result = await handle({
                "repo_url": "https://github.com/test/repo",
                "file_path": "src/app.py",
                "branch": "main",
                "format": "raw",
            })

            assert len(result) == 1
            assert result[0].text == "print('hi')\n"

            mock_service.get_file_content.assert_called_once_with(
                repo_url="https://github.com/test/repo",
                file_path="src/app.py",
                branch="main",
            )


class TestCreateTestPRIntegration:
    """Integration tests for create_test_pr tool."""
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Missing required fields return error."""
        from pytest_pipeline_mcp.handlers.github.create_test_pr import handle
        
        result = await handle({"repo_url": "https://github.com/test/repo"})
        assert len(result) == 1
        assert "Error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_missing_token_error(self):
        """Missing token returns auth error."""
        from pytest_pipeline_mcp.handlers.github.create_test_pr import handle
        
        # Temporarily ensure no token
        import os
        old_token = os.environ.get("GITHUB_TOKEN")
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        
        try:
            result = await handle({
                "repo_url": "https://github.com/test/repo",
                "test_code": "def test_x(): pass",
                "target_file": "src/module.py"
            })
            assert "token" in result[0].text.lower()
        finally:
            if old_token:
                os.environ["GITHUB_TOKEN"] = old_token


class TestCommentTestResultsIntegration:
    """Integration tests for comment_test_results tool."""
    
    @pytest.mark.asyncio
    async def test_missing_pr_number(self):
        """Missing pr_number returns error."""
        from pytest_pipeline_mcp.handlers.github.comment_test_results import handle
        
        result = await handle({
            "repo_url": "https://github.com/test/repo",
            "test_results": "5 passed"
        })
        assert len(result) == 1
        assert "Error" in result[0].text
