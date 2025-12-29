"""
Generation Service - Business logic for test generation.

Orchestrates the full pipeline:
1. Load code
2. Analyze code
3. Generate tests (template or AI-enhanced)
4. Optionally save to file

Returns the existing GeneratedTest model - no duplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Import existing domain models and functions
from ..core.generators import GeneratedTest, generate_tests, generate_tests_with_ai
from .analysis import AnalysisService
from .base import ErrorCode, ServiceResult
from .code_loader import CodeLoader


@dataclass(frozen=True)
class GenerationMetadata:
    """
    Additional metadata about the generation.
    
    Attributes:
        mode: "Template" or "AI-enhanced"
        function_count: Number of functions in source
        class_count: Number of classes in source
        saved_to: File path if saved, None otherwise
    """
    mode: str
    function_count: int
    class_count: int
    saved_to: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    """
    Complete result of test generation.
    
    Combines the GeneratedTest with metadata about the operation.
    
    Attributes:
        tests: The generated test cases
        metadata: Additional information about the generation
    """
    tests: GeneratedTest
    metadata: GenerationMetadata


class GenerationService:
    """
    Service for generating pytest tests.
    
    Orchestrates:
    1. Code loading and analysis
    2. Template-based or AI-enhanced generation
    3. Optional file output
    
    This class is stateless - inject dependencies via __init__.
    """

    def __init__(
        self,
        code_loader: CodeLoader | None = None,
        analysis_service: AnalysisService | None = None
    ):
        """
        Initialize the generation service.
        
        Args:
            code_loader: CodeLoader instance (creates default if None)
            analysis_service: AnalysisService instance (creates default if None)
        """
        self._loader = code_loader or CodeLoader()
        # Share the loader with analysis service for consistency
        self._analyzer = analysis_service or AnalysisService(self._loader)

    def generate(
        self,
        code: str | None = None,
        file_path: str | None = None,
        include_edge_cases: bool = True,
        use_ai: bool = False,
        api_key: str | None = None,
        output_path: str | None = None
    ) -> ServiceResult[GenerationResult]:
        """
        Generate tests for Python code.
        
        Args:
            code: Direct code string
            file_path: Path to Python file
            include_edge_cases: Whether to generate boundary tests
            use_ai: Whether to use AI enhancement
            api_key: OpenAI API key (uses env var if not provided)
            output_path: Path to save generated tests
            
        Returns:
            ServiceResult containing GenerationResult
            
        Example:
            service = GenerationService()
            result = service.generate(code="def add(a, b): return a + b")
            if result.success:
                print(result.data.tests.to_code())
        """
        # Step 1: Load and analyze code
        analyze_result = self._analyzer.analyze_with_metadata(
            code=code,
            file_path=file_path
        )

        if not analyze_result.success:
            return ServiceResult.fail(
                analyze_result.error.code,
                f"Cannot generate tests: {analyze_result.error.message}",
                analyze_result.error.details
            )

        analysis, loaded = analyze_result.data

        # Step 2: Generate tests
        if use_ai:
            tests = generate_tests_with_ai(
                analysis=analysis,
                source_code=loaded.content,
                module_name=loaded.module_name,
                include_edge_cases=include_edge_cases,
                api_key=api_key
            )
            mode = "AI-enhanced"
        else:
            tests = generate_tests(
                analysis=analysis,
                source_code=loaded.content,
                module_name=loaded.module_name,
                include_edge_cases=include_edge_cases
            )
            mode = "Template"

        # Step 3: Optionally save to file
        saved_to = None
        if output_path:
            save_result = self._save_to_file(tests.to_code(), output_path)
            if save_result.success:
                saved_to = output_path
            else:
                # Add warning but don't fail the whole operation
                tests.warnings.append(
                    f"Could not save to file: {save_result.error.message}"
                )

        # Step 4: Build result
        metadata = GenerationMetadata(
            mode=mode,
            function_count=len(analysis.functions),
            class_count=len(analysis.classes),
            saved_to=saved_to
        )

        return ServiceResult.ok(GenerationResult(
            tests=tests,
            metadata=metadata
        ))

    def generate_code_only(
        self,
        code: str | None = None,
        file_path: str | None = None,
        include_edge_cases: bool = True,
        use_ai: bool = False,
        api_key: str | None = None
    ) -> ServiceResult[str]:
        """
        Generate tests and return just the code string.
        
        Convenience method when you only need the test code.
        
        Args:
            code: Direct code string
            file_path: Path to Python file
            include_edge_cases: Whether to generate boundary tests
            use_ai: Whether to use AI enhancement
            api_key: OpenAI API key
            
        Returns:
            ServiceResult containing test code as string
        """
        result = self.generate(
            code=code,
            file_path=file_path,
            include_edge_cases=include_edge_cases,
            use_ai=use_ai,
            api_key=api_key,
            output_path=None
        )

        if not result.success:
            return ServiceResult.fail(
                result.error.code,
                result.error.message,
                result.error.details
            )

        return ServiceResult.ok(result.data.tests.to_code())

    def _save_to_file(self, content: str, path: str) -> ServiceResult[str]:
        """
        Save content to a file.
        
        Args:
            content: Content to write
            path: Destination path
            
        Returns:
            ServiceResult with path on success
        """
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return ServiceResult.ok(path)
        except PermissionError:
            return ServiceResult.fail(
                ErrorCode.PERMISSION_DENIED,
                f"Permission denied: {path}"
            )
        except Exception as e:
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                f"Failed to save file: {e}"
            )
