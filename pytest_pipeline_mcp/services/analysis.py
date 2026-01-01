"""
Analysis Service - Business logic for code analysis.

Wraps the analyzer module with:
- Input validation via CodeLoader
- Structured error handling via ServiceResult
- Clean separation from MCP presentation

Returns the existing AnalysisResult model - no duplication.
"""

from __future__ import annotations

# Import existing domain models
from ..core.analyzer import AnalysisResult, analyze_code
from .base import ErrorCode, ServiceResult
from .code_loader import CodeLoader, LoadedCode


class AnalysisService:
    """
    Service for analyzing Python code.
    
    Orchestrates:
    1. Code loading (from file or string)
    2. Analysis via analyzer module
    3. Error handling and result wrapping
    
    This class is stateless - inject dependencies via __init__.
    """

    def __init__(self, code_loader: CodeLoader | None = None):
        """
        Initialize the analysis service.
        
        Args:
            code_loader: CodeLoader instance (creates default if None)
        """
        self._loader = code_loader or CodeLoader()

    def analyze(
        self,
        code: str | None = None,
        file_path: str | None = None
    ) -> ServiceResult[AnalysisResult]:
        """
        Analyze Python code.
        
        Args:
            code: Direct code string
            file_path: Path to Python file
            
        Returns:
            ServiceResult containing AnalysisResult on success
            
        Example:
            service = AnalysisService()
            result = service.analyze(code="def add(a, b): return a + b")
            if result.success:
                print(f"Found {len(result.data.functions)} functions")
        """
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
        """
        Analyze code and return both analysis and load metadata.
        
        Useful when you need the module name or source path
        for subsequent operations.
        
        Args:
            code: Direct code string
            file_path: Path to Python file
            
        Returns:
            ServiceResult containing (AnalysisResult, LoadedCode) tuple
        """
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
