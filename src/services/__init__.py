"""
Services Layer - Business logic decoupled from presentation.

This package provides service classes that encapsulate business logic,
making it:
- Testable without MCP infrastructure
- Reusable across different interfaces (CLI, REST, MCP)
- Clean separation of concerns

Design Principles:
-----------------
1. Services return EXISTING domain models (AnalysisResult, etc.)
2. ServiceResult wraps success/failure uniformly
3. Dependencies are injected via __init__ (no globals)
4. All services are stateless

Quick Start:
-----------
    from src.services import AnalysisService, GenerationService
    
    # Analyze code
    analyzer = AnalysisService()
    result = analyzer.analyze(code="def add(a, b): return a + b")
    if result.success:
        print(f"Functions: {len(result.data.functions)}")
    
    # Generate tests
    generator = GenerationService()
    result = generator.generate(code="def add(a, b): return a + b")
    if result.success:
        print(result.data.tests.to_code())

Architecture:
------------
    ┌─────────────────────────────────────────────────────────┐
    │                     server.py (thin)                     │
    │  - Parse MCP arguments                                   │
    │  - Call services                                         │
    │  - Format TextContent responses                          │
    └────────────────────────┬────────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────────┐
    │                   services/ (this package)               │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
    │  │AnalysisServ│  │GenerationSer│  │ExecutionService│  │
    │  │             │  │             │  │                 │  │
    │  │ analyze()   │  │ generate()  │  │ run()          │  │
    │  └──────┬──────┘  └──────┬──────┘  └────────┬───────┘  │
    │         │                │                   │          │
    │         └────────────────┼───────────────────┘          │
    │                          │                              │
    │              ┌───────────▼────────────┐                 │
    │              │     CodeLoader         │                 │
    │              │  (shared dependency)   │                 │
    │              └────────────────────────┘                 │
    └─────────────────────────────────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────────┐
    │              analyzer/, generators/, runner/, fixer/     │
    │                    (existing modules)                    │
    └─────────────────────────────────────────────────────────┘
"""

# Base utilities
from .base import (
    ServiceResult,
    ServiceError,
    ErrorCode,
)

# Code loading
from .code_loader import (
    CodeLoader,
    LoadedCode,
)

# Services
from .analysis import AnalysisService
from .generation import GenerationService, GenerationResult, GenerationMetadata
from .execution import ExecutionService
from .fixing import FixingService
from .github import GitHubService, CloneResult, PRInfo, CommentInfo


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
]


# =============================================================================
# Convenience factory functions
# =============================================================================

def create_analysis_service(code_loader: CodeLoader | None = None) -> AnalysisService:
    """
    Create an AnalysisService with optional custom CodeLoader.
    
    Args:
        code_loader: Custom CodeLoader (uses default if None)
        
    Returns:
        Configured AnalysisService
    """
    return AnalysisService(code_loader=code_loader)


def create_generation_service(
    code_loader: CodeLoader | None = None,
    analysis_service: AnalysisService | None = None
) -> GenerationService:
    """
    Create a GenerationService with optional custom dependencies.
    
    Args:
        code_loader: Custom CodeLoader
        analysis_service: Custom AnalysisService
        
    Returns:
        Configured GenerationService
    """
    return GenerationService(
        code_loader=code_loader,
        analysis_service=analysis_service
    )


def create_execution_service() -> ExecutionService:
    """
    Create an ExecutionService.
    
    Returns:
        Configured ExecutionService
    """
    return ExecutionService()


def create_fixing_service() -> FixingService:
    """
    Create a FixingService.
    
    Returns:
        Configured FixingService
    """
    return FixingService()
