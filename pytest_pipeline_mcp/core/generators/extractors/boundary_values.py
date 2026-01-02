"""
Boundary Values - Generate edge case test inputs based on types.

Provides safe, type-appropriate boundary values for testing.
"""

from dataclasses import dataclass


@dataclass
class BoundaryValue:
    """A boundary value for testing."""
    value: str          # Python literal: "0", '""', "[]"
    description: str    # "zero", "empty string", "empty list"
    category: str       # "zero", "empty", "negative", "large"


# Boundary values for each type
BOUNDARY_VALUES = {
    "int": [
        BoundaryValue("0", "zero", "zero"),
        BoundaryValue("1", "one", "small"),
        BoundaryValue("-1", "negative one", "negative"),
        BoundaryValue("1000000", "large number", "large"),
    ],
    "float": [
        BoundaryValue("0.0", "zero", "zero"),
        BoundaryValue("1.0", "one", "small"),
        BoundaryValue("-1.0", "negative one", "negative"),
        BoundaryValue("0.5", "fraction", "fraction"),
        BoundaryValue("1e10", "large number", "large"),
    ],
    "str": [
        BoundaryValue('""', "empty string", "empty"),
        BoundaryValue('"a"', "single char", "small"),
        BoundaryValue('"hello"', "normal string", "normal"),
        BoundaryValue('" "', "whitespace", "whitespace"),
        BoundaryValue('"a" * 1000', "long string", "large"),
    ],
    "bool": [
        BoundaryValue("True", "true", "true"),
        BoundaryValue("False", "false", "false"),
    ],
    "list": [
        BoundaryValue("[]", "empty list", "empty"),
        BoundaryValue("[1]", "single item", "small"),
        BoundaryValue("[1, 2, 3]", "multiple items", "normal"),
    ],
    "list[int]": [
        BoundaryValue("[]", "empty list", "empty"),
        BoundaryValue("[0]", "single zero", "small"),
        BoundaryValue("[1, 2, 3]", "multiple ints", "normal"),
        BoundaryValue("[-1, 0, 1]", "with negatives", "mixed"),
    ],
    "list[str]": [
        BoundaryValue("[]", "empty list", "empty"),
        BoundaryValue('[""]', "list with empty string", "edge"),
        BoundaryValue('["a", "b"]', "multiple strings", "normal"),
    ],
    "dict": [
        BoundaryValue("{}", "empty dict", "empty"),
        BoundaryValue('{"a": 1}', "single item", "small"),
    ],
    "Optional[int]": [
        BoundaryValue("None", "none", "none"),
        BoundaryValue("0", "zero", "zero"),
        BoundaryValue("1", "one", "small"),
    ],
    "Optional[str]": [
        BoundaryValue("None", "none", "none"),
        BoundaryValue('""', "empty string", "empty"),
        BoundaryValue('"test"', "normal string", "normal"),
    ],
}

# Default value for each type (for basic tests)
DEFAULT_VALUES = {
    "int": "0",
    "float": "0.0",
    "str": '""',
    "bool": "True",
    "list": "[]",
    "dict": "{}",
    "set": "set()",
    "tuple": "()",
    "bytes": 'b""',
    "None": "None",
    "Any": "None",
}

# Guess defaults by parameter name patterns
NAME_PATTERNS = {
    # Numeric names → int
    ('a', 'b', 'x', 'y', 'n', 'i', 'j', 'k', 'num', 'number', 'count', 'index', 'size', 'length'): "0",
    # String names → str
    ('s', 'name', 'text', 'string', 'msg', 'message', 'title', 'label', 'key', 'value', 'path', 'url'): '""',
    # Collection names → list
    ('items', 'values', 'elements', 'data', 'args', 'results'): "[]",
    # Dict names → dict
    ('config', 'options', 'params', 'kwargs', 'settings', 'mapping'): "{}",
    # Boolean names → bool
    ('flag', 'enabled', 'active', 'valid', 'ok', 'success', 'is_valid', 'has_value'): "True",
}

def get_default_value(type_hint: str | None, param_name: str | None = None) -> str:
    """Return a safe default Python literal for the given type hint."""

    if type_hint:
        
        # Clean type
        clean = type_hint.strip()

        # Check direct match
        if clean in DEFAULT_VALUES:
            return DEFAULT_VALUES[clean]

        # Handle Optional[X] - default to None
        if clean.startswith("Optional[") or " | None" in clean:
            return "None"

        # Handle list[X] - return empty list
        if clean.startswith("list["):
            return "[]"

        # Handle dict[X, Y] - return empty dict
        if clean.startswith("dict["):
            return "{}"

        # Get base type
        base = clean.split("[")[0]
        if base in DEFAULT_VALUES:
            return DEFAULT_VALUES[base]

    if param_name:
        clean_name = param_name.lower().lstrip('_')
        
        for names, default in NAME_PATTERNS.items():
            if clean_name in names or any(clean_name.startswith(n) for n in names):
                return default
    
    # Last resort: return 0 (safer than None for most operations)
    return "0"


def generate_boundary_values(type_hint: str | None) -> list[BoundaryValue]:
    """
    Generate boundary test values for a type.
    
    Args:
        type_hint: Type annotation string
        
    Returns:
        List of BoundaryValue objects
    """
    if not type_hint:
        return []

    clean = type_hint.strip()

    # Check direct match
    if clean in BOUNDARY_VALUES:
        return BOUNDARY_VALUES[clean]

    # Handle Optional[X]
    if clean.startswith("Optional["):
        inner = clean[9:-1]
        values = [BoundaryValue("None", "none", "none")]
        if inner in BOUNDARY_VALUES:
            values.extend(BOUNDARY_VALUES[inner])
        return values

    # Handle X | None
    if " | None" in clean:
        base = clean.replace(" | None", "").strip()
        values = [BoundaryValue("None", "none", "none")]
        if base in BOUNDARY_VALUES:
            values.extend(BOUNDARY_VALUES[base])
        return values

    # Get base type
    base = clean.split("[")[0]
    if base in BOUNDARY_VALUES:
        return BOUNDARY_VALUES[base]

    return []


def get_boundary_test_name(description: str) -> str:
    """Convert boundary description to test name suffix."""
    return description.replace(" ", "_").replace("-", "_")
