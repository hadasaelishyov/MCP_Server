"""Syntax Validator - Check if Python code is valid."""

import ast
from dataclasses import dataclass


@dataclass
class SyntaxResult:
    """Result of syntax validation."""
    is_valid: bool
    error_message: str | None = None
    error_line: int | None = None
    error_offset: int | None = None


def validate_syntax(code: str) -> SyntaxResult:
    """Validate Python syntax and return a structured result."""

    try:
        ast.parse(code)
        return SyntaxResult(is_valid=True)
    except SyntaxError as e:
        return SyntaxResult(
            is_valid=False,
            error_message=e.msg,
            error_line=e.lineno,
            error_offset=e.offset
        )
