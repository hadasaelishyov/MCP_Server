"""Analysis service.

Loads code via CodeLoader and delegates analysis to the core analyzer.
"""


from __future__ import annotations

# Import existing domain models
from ..core.analyzer import AnalysisResult, analyze_code
from .base import ErrorCode, ServiceResult
from .code_loader import CodeLoader, LoadedCode


class AnalysisService:
    """Analyze Python source code (load → analyze) and return AnalysisResult in ServiceResult."""

    def __init__(self, code_loader: CodeLoader | None = None):
        self._loader = code_loader or CodeLoader()

    def analyze(
        self,
        code: str | None = None,
        file_path: str | None = None
    ) -> ServiceResult[AnalysisResult]:
        """Analyze code provided via `code` or `file_path`."""

        # Step 1: Load code
        load_result = self._loader.load(code=code, file_path=file_path)

        if not load_result.success:
            return ServiceResult.fail(
                load_result.error.code,
                load_result.error.message,
                load_result.error.details
            )

        loaded = load_result.data

        # Step 2: Run analysis
        analysis = analyze_code(loaded.content)

        # Step 3: Check for analysis errors
        if not analysis.valid:
            return ServiceResult.fail(
                ErrorCode.SYNTAX_ERROR,
                analysis.error or "Analysis failed"
            )

        return ServiceResult.ok(analysis)

    def analyze_with_metadata(
        self,
        code: str | None = None,
        file_path: str | None = None
    ) -> ServiceResult[tuple[AnalysisResult, LoadedCode]]:
        """Analyze code and also return load metadata (e.g., module name / source path)."""

        # Step 1: Load code
        load_result = self._loader.load(code=code, file_path=file_path)

        if not load_result.success:
            return ServiceResult.fail(
                load_result.error.code,
                load_result.error.message,
                load_result.error.details
            )

        loaded = load_result.data

        # Step 2: Run analysis
        analysis = analyze_code(loaded.content)

        if not analysis.valid:
            return ServiceResult.fail(
                ErrorCode.SYNTAX_ERROR,
                analysis.error or "Analysis failed"
            )

        return ServiceResult.ok((analysis, loaded))
