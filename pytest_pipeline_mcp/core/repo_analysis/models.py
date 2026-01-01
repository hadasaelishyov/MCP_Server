from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class FileAnalysis:
    """Information about a single file in repository."""
    relative_path: str
    functions_count: int
    classes_count: int
    is_test_file: bool
    complexity: float
    type_hint_coverage: float
    warnings: list[str] = field(default_factory=list)

    @property
    def needs_tests(self) -> bool:
        return (not self.is_test_file) and (self.functions_count > 0 or self.classes_count > 0)

@dataclass
class RepositoryAnalysis:
    repo_url: str
    branch: str
    files: list[FileAnalysis]

    @property
    def total_files(self) -> int:
        """Total number of Python files in repository."""
        return len(self.files)

    @property
    def files_needing_tests(self) -> int:
        """Number of files that need test coverage."""
        return sum(1 for f in self.files if f.needs_tests)

    @property
    def total_functions(self) -> int:
        """Total number of functions across all files."""
        return sum(f.functions_count for f in self.files)

    @property
    def total_classes(self) -> int:
        """Total number of classes across all files."""
        return sum(f.classes_count for f in self.files)