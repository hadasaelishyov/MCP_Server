"""
Base interface for test generators.
Allows swapping between template and AI generators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..analyzer.models import ClassInfo, FunctionInfo


@dataclass
class GeneratedTestCase:
    """A single test case."""
    name: str                          # "test_add_basic"
    description: str                   # "Test add with basic inputs"
    body: list[str]                    # Lines of test code

    # Evidence tracking (for transparency)
    evidence_source: str = "template"  # "template" | "doctest" | "type_hint" | "ai"


@dataclass
class GeneratedTest:
    """Complete generated test file."""
    module_name: str
    imports: list[str]
    test_cases: list[GeneratedTestCase]
    warnings: list[str] = field(default_factory=list)

    def to_code(self) -> str:
        """Convert to executable Python test code."""
        lines = []

        # Module docstring
        lines.append(f'"""Tests for {self.module_name}."""')
        lines.append("")

        # Imports
        lines.append("import pytest")
        if self.imports:
            imports_str = ", ".join(self.imports)
            lines.append(f"from {self.module_name} import {imports_str}")
        lines.append("")
        lines.append("")

        # Test functions
        for test in self.test_cases:
            lines.append(f"def {test.name}():")
            lines.append(f'    """{test.description}"""')

            for body_line in test.body:
                # Handle multi-line statements (like 'with' blocks)
                if '\n' in body_line:
                    sub_lines = body_line.split('\n')
                    for i, sub_line in enumerate(sub_lines):
                        if i == 0:
                            # First line gets normal indent
                            lines.append(f"    {sub_line}")
                        else:
                            # Subsequent lines get extra indent (inside with block)
                            lines.append(f"        {sub_line}")
                else:
                    lines.append(f"    {body_line}")

            lines.append("")
            lines.append("")

        return "\n".join(lines)


class TestGeneratorBase(ABC):
    """Abstract base class for test generators."""

    @abstractmethod
    def generate_for_function(
        self,
        func: FunctionInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate test cases for a single function."""
        pass

    @abstractmethod
    def generate_for_class(
        self,
        cls: ClassInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate test cases for a class."""
        pass
