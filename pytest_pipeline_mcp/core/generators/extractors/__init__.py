"""
Evidence-based test enrichment - Layer 2.

This package provides extractors that find evidence in source code
to generate better tests:
- Doctest examples from docstrings
- Type assertions from type hints
- Exception tests from raise statements
- Boundary values from parameter types
"""
from .boundary_values import generate_boundary_values
from .doctest_extractor import extract_doctests
from .exception_detector import detect_exceptions
from .type_assertions import generate_type_assertions

__all__ = [
    "extract_doctests",
    "generate_type_assertions",
    "detect_exceptions",
    "generate_boundary_values"
]
