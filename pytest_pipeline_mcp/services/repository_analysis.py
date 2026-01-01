"""Repository analysis service.

Clones a repo, discovers Python files, and runs per-file analysis to identify candidates for tests.
"""

from __future__ import annotations
from pathlib import Path

from ..core.repo_analysis.models import FileAnalysis, RepositoryAnalysis
from .analysis import AnalysisService
from .base import ServiceResult
from .github import GitHubService


class RepositoryAnalysisService:
    """Analyze a GitHub repository by cloning, discovering Python files, and analyzing each file."""

    _DEFAULT_EXCLUDED_PARTS = {"__pycache__", "venv", ".venv", "node_modules", "dist", "build"}

    def __init__(
        self,
        github_service: GitHubService | None = None,
        analysis_service: AnalysisService | None = None,
        excluded_parts: set[str] | None = None,
    ):
        
        self._github = github_service or GitHubService()
        self._analysis = analysis_service or AnalysisService()
        self._excluded = excluded_parts or self._DEFAULT_EXCLUDED_PARTS

    def analyze_repository(
        self,
        repo_url: str,
        branch: str = "main",
        path_filter: str | None = None,
    ) -> ServiceResult[RepositoryAnalysis]:
        clone_result = self._github.clone_repository(repo_url, branch)
        if not clone_result.success:
            return ServiceResult.fail(clone_result.error.code, clone_result.error.message, clone_result.error.details)

        clone_info = clone_result.data
        repo_path = clone_info.path
        actual_branch = clone_info.branch

        try:
            py_files = self._discover_python_files(repo_path, path_filter)
            files_analyzed = [self._analyze_file(repo_path, f) for f in py_files]

            return ServiceResult.ok(
                RepositoryAnalysis(repo_url=repo_url, branch=actual_branch, files=files_analyzed)
            )
        finally:
            self._github.cleanup_clone(repo_path)

    def _discover_python_files(self, repo_path: Path, path_filter: str | None) -> list[Path]:
        candidates = list(repo_path.glob(path_filter)) if path_filter else list(repo_path.rglob("*.py"))
        return [p for p in candidates if not self._is_excluded_path(p)]

    def _is_excluded_path(self, path: Path) -> bool:
        for part in path.parts:
            if part.startswith("."):
                return True
            if part in self._excluded:
                return True
        return False

    def _is_test_file(self, relative_path: str, filename: str) -> bool:
        name = filename.lower()
        return ("test" in name or name.startswith("test_") or "/tests/" in relative_path or "\\tests\\" in relative_path)

    def _analyze_file(self, repo_path: Path, py_file: Path) -> FileAnalysis:
        relative_path = str(py_file.relative_to(repo_path))
        is_test_file = self._is_test_file(relative_path, py_file.name)

        result = self._analysis.analyze(file_path=str(py_file))
        if result.success:
            a = result.data
            return FileAnalysis(
                relative_path=relative_path,
                functions_count=a.total_functions,
                classes_count=a.total_classes,
                is_test_file=is_test_file,
                complexity=a.average_complexity,
                type_hint_coverage=a.type_hint_coverage,
                warnings=a.warnings[:3],
            )

        return FileAnalysis(
            relative_path=relative_path,
            functions_count=0,
            classes_count=0,
            is_test_file=is_test_file,
            complexity=0,
            type_hint_coverage=0,
            warnings=[f"Parse error: {result.error.message}"],
        )
