"""
Code Loader Service - Handles loading Python code from various sources.

Extracts and centralizes the code loading logic that was in server.py's
_get_code() function. This makes it:
- Reusable across services
- Testable in isolation
- Configurable via dependency injection
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import ServiceResult, ErrorCode

# Import constants from the project
from ..constants import MAX_CODE_SIZE, ALLOWED_EXTENSIONS


@dataclass(frozen=True)
class LoadedCode:
    """
    Result of successfully loading code.
    
    Immutable to prevent accidental modification.
    
    Attributes:
        content: The Python source code
        module_name: Detected or default module name for imports
        source_path: Original file path (None if loaded from string)
    """
    content: str
    module_name: str
    source_path: str | None = None


class CodeLoader:
    """
    Loads Python code from files or direct input.
    
    Handles:
    - File path validation (extension, existence, permissions)
    - Size validation
    - Module name extraction
    - Fallback to direct code when file unavailable
    
    This class is stateless - all configuration is passed to __init__
    and all state is passed to methods.
    """
    
    def __init__(
        self,
        max_size: int = MAX_CODE_SIZE,
        allowed_extensions: frozenset[str] = ALLOWED_EXTENSIONS
    ):
        """
        Initialize the code loader.
        
        Args:
            max_size: Maximum allowed code size in bytes
            allowed_extensions: Set of allowed file extensions
        """
        self._max_size = max_size
        self._allowed_extensions = allowed_extensions
    
    def load(
        self,
        code: str | None = None,
        file_path: str | None = None
    ) -> ServiceResult[LoadedCode]:
        """
        Load code from file path or direct input.
        
        Priority:
        1. If file_path provided and file exists → load from file
        2. If file_path provided but file missing → use code as fallback
        3. If only code provided → use code directly
        4. If neither provided → error
        
        Args:
            code: Direct code string (optional)
            file_path: Path to Python file (optional)
            
        Returns:
            ServiceResult with LoadedCode on success, error on failure
        """
        if file_path:
            return self._load_from_file(file_path, fallback_code=code)
        elif code is not None:
            return self._load_from_string(code)
        else:
            return ServiceResult.fail(
                ErrorCode.MISSING_INPUT,
                "Please provide either 'file_path' or 'code'"
            )
    
    def _load_from_file(
        self,
        file_path: str,
        fallback_code: str | None = None
    ) -> ServiceResult[LoadedCode]:
        """
        Load code from a file path.
        
        Args:
            file_path: Path to Python file
            fallback_code: Code to use if file can't be read
            
        Returns:
            ServiceResult with LoadedCode
        """
        path = Path(file_path)
        module_name = self._extract_module_name(file_path)
        
        # Validate extension
        if path.suffix not in self._allowed_extensions:
            return ServiceResult.fail(
                ErrorCode.INVALID_EXTENSION,
                f"Only Python files allowed (got {path.suffix})",
                details={
                    "extension": path.suffix,
                    "allowed": list(self._allowed_extensions)
                }
            )
        
        # Check file exists
        if not path.exists():
            if fallback_code is not None:
                return self._load_from_string(fallback_code, module_name)
            return ServiceResult.fail(
                ErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}"
            )
        
        # Check it's a file, not directory
        if not path.is_file():
            return ServiceResult.fail(
                ErrorCode.VALIDATION_ERROR,
                f"Path is not a file: {file_path}"
            )
        
        # Try to read file
        try:
            content = path.read_text(encoding="utf-8")
        except PermissionError:
            if fallback_code is not None:
                return self._load_from_string(fallback_code, module_name)
            return ServiceResult.fail(
                ErrorCode.PERMISSION_DENIED,
                f"Permission denied: {file_path}"
            )
        except Exception as e:
            if fallback_code is not None:
                return self._load_from_string(fallback_code, module_name)
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                f"Error reading file: {e}"
            )
        
        # Validate size
        if len(content) > self._max_size:
            return ServiceResult.fail(
                ErrorCode.FILE_TOO_LARGE,
                f"File too large: {len(content):,} bytes (max: {self._max_size:,})",
                details={"size": len(content), "max_size": self._max_size}
            )
        
        return ServiceResult.ok(LoadedCode(
            content=content,
            module_name=module_name,
            source_path=file_path
        ))
    
    def _load_from_string(
        self,
        code: str,
        module_name: str = "module"
    ) -> ServiceResult[LoadedCode]:
        """
        Load code from a direct string.
        
        Args:
            code: Python source code
            module_name: Module name for imports
            
        Returns:
            ServiceResult with LoadedCode
        """
        # Validate size
        if len(code) > self._max_size:
            return ServiceResult.fail(
                ErrorCode.FILE_TOO_LARGE,
                f"Code too large: {len(code):,} bytes (max: {self._max_size:,})",
                details={"size": len(code), "max_size": self._max_size}
            )
        
        return ServiceResult.ok(LoadedCode(
            content=code,
            module_name=module_name,
            source_path=None
        ))
    
    def _extract_module_name(self, file_path: str) -> str:
        """
        Extract module name from file path.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Module name (filename without extension)
        """
        return Path(file_path).stem
