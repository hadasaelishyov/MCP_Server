"""
Shared constants used across the project.
"""

from typing import Final

# Types that can be safely used with isinstance
SIMPLE_TYPES: Final[frozenset[str]] = frozenset({
    "int", "str", "float", "bool", "list", "dict",
    "set", "tuple", "bytes", "bytearray"
})

# Special isinstance mappings (float should accept int)
ISINSTANCE_MAPPING: Final[dict[str, str]] = {
    "int": "int",
    "str": "str",
    "float": "(int, float)",
    "bool": "bool",
    "list": "list",
    "dict": "dict",
    "set": "set",
    "tuple": "tuple",
    "bytes": "bytes",
    "bytearray": "bytearray",
}

# Standard library modules to skip when detecting imports
STDLIB_MODULES: Final[frozenset[str]] = frozenset({
    'pytest', 'unittest', 'typing', 'collections',
    'os', 'sys', 'json', 're', 'ast', 'pathlib'
})

# File constraints
MAX_CODE_SIZE: Final[int] = 1_000_000  # 1MB
ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({'.py'})

# AI Configuration
DEFAULT_AI_MODEL: Final[str] = "gpt-4o-mini"
AI_TEMPERATURE: Final[float] = 0.2
AI_MAX_TOKENS: Final[int] = 2000

# Test execution
TEST_TIMEOUT_SECONDS: Final[int] = 30