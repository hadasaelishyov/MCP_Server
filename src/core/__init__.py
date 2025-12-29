"""
Core - Pure business logic for pytest generation.

This package contains reusable logic with NO dependencies on:
- MCP (Model Context Protocol)
- Services layer
- External frameworks

Can be used independently in CLI, REST API, or any other interface.

Modules:
- analyzer: Code parsing and analysis
- generators: Test case generation
- runner: Test execution
- fixer: AI-powered code fixing
"""

from .analyzer import analyze_code, analyze_file, AnalysisResult, FunctionInfo, ClassInfo
from .generators import generate_tests, GeneratedTest, GeneratedTestCase, TemplateGenerator
from .runner import run_tests, RunResult, PytestRunner
from .fixer import fix_code, FixResult, CodeFixer

__all__ = [
    # Analyzer
    "analyze_code",
    "analyze_file",
    "AnalysisResult",
    "FunctionInfo",
    "ClassInfo",
    # Generators
    "generate_tests",
    "GeneratedTest",
    "GeneratedTestCase",
    "TemplateGenerator",
    # Runner
    "run_tests",
    "RunResult",
    "PytestRunner",
    # Fixer
    "fix_code",
    "FixResult",
    "CodeFixer",
]