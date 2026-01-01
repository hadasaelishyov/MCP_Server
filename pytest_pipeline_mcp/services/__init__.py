"""Services package.

Exposes stateless service classes and shared result types used by handlers (MCP/GitHub).
"""


# Base utilities
# Services
from .analysis import AnalysisService
from .base import (
    ErrorCode,
    ServiceError,
    ServiceResult,
)

# Code loading
from .code_loader import (
    CodeLoader,
    LoadedCode,
)
from .execution import ExecutionService
from .fixing import FixingService
from .generation import GenerationMetadata, GenerationResult, GenerationService
from .github import CloneResult, CommentInfo, GitHubService, PRInfo
from .repository_analysis import RepositoryAnalysisService

__all__ = [
    # Base
    "ServiceResult",
    "ServiceError",
    "ErrorCode",
    # Code loading
    "CodeLoader",
    "LoadedCode",
    # Services
    "AnalysisService",
    "GenerationService",
    "GenerationResult",
    "GenerationMetadata",
    "ExecutionService",
    "FixingService",
    # GitHub
    "GitHubService",
    "CloneResult",
    "PRInfo",
    "CommentInfo",
    "RepositoryAnalysisService",

]


# =============================================================================
# Convenience factory functions
# =============================================================================

def create_analysis_service(code_loader: CodeLoader | None = None) -> AnalysisService:
    """Factory for AnalysisService (optionally inject a CodeLoader)."""

    return AnalysisService(code_loader=code_loader)


def create_generation_service(
    code_loader: CodeLoader | None = None,
    analysis_service: AnalysisService | None = None
) -> GenerationService:
    """Factory for GenerationService (optionally inject dependencies)."""

    return GenerationService(
        code_loader=code_loader,
        analysis_service=analysis_service
    )


def create_execution_service() -> ExecutionService:
    """Factory for ExecutionService."""

    return ExecutionService()


def create_fixing_service() -> FixingService:
    """Factory for FixingService."""

    return FixingService()
