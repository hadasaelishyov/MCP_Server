"""
Type Assertions - Generate assertions based on type hints.

Safely handles:
- Simple types (int, str, float, bool, list, dict, etc.)
- Optional types (Optional[X], X | None)
- Union types (X | Y, Union[X, Y])
- Union with None (X | Y | None)
- Generic containers (list[X], dict[K, V])
- Complex unions in containers (list[X | None])

When type is too complex to safely check, falls back to container-only checks.
Principle: Better weak than wrong - never generate invalid isinstance checks.
"""

from dataclasses import dataclass
from .....constants import SIMPLE_TYPES, ISINSTANCE_MAPPING

@dataclass
class ParsedType:
    """Parsed type hint information."""
    base_types: list[str]  # Non-None types like ["str", "int"]
    allows_none: bool      # Whether None is allowed
    is_valid: bool         # Whether we can generate safe isinstance checks



def parse_type_hint(type_str: str) -> ParsedType:
    """
    Parse a type hint string into components.
    
    Handles:
    - Simple: "str", "int", "float"
    - None: "None"
    - Optional: "Optional[str]"
    - Union with None: "str | None", "int | str | None"
    - Union without None: "int | str"
    - typing.Union: "Union[str, int]"
    
    Args:
        type_str: Type annotation string
        
    Returns:
        ParsedType with base_types, allows_none, and is_valid
    """
    type_str = type_str.strip()
    
    # Handle None
    if type_str == "None":
        return ParsedType(base_types=[], allows_none=True, is_valid=True)
    
    # Handle Optional[X]
    if type_str.startswith("Optional[") and type_str.endswith("]"):
        inner = type_str[9:-1].strip()
        inner_parsed = parse_type_hint(inner)
        return ParsedType(
            base_types=inner_parsed.base_types,
            allows_none=True,
            is_valid=inner_parsed.is_valid
        )
    
    # Handle typing.Optional[X]
    if type_str.startswith("typing.Optional[") and type_str.endswith("]"):
        inner = type_str[16:-1].strip()
        inner_parsed = parse_type_hint(inner)
        return ParsedType(
            base_types=inner_parsed.base_types,
            allows_none=True,
            is_valid=inner_parsed.is_valid
        )
    
    # Handle Union[X, Y, ...]
    if type_str.startswith("Union[") and type_str.endswith("]"):
        inner = type_str[6:-1]
        parts = _split_comma_parts(inner)
        return _parse_type_parts(parts)
    
    # Handle typing.Union[X, Y, ...]
    if type_str.startswith("typing.Union[") and type_str.endswith("]"):
        inner = type_str[13:-1]
        parts = _split_comma_parts(inner)
        return _parse_type_parts(parts)
    
    # Handle X | Y | Z syntax (PEP 604)
    if " | " in type_str:
        parts = [p.strip() for p in type_str.split(" | ")]
        return _parse_type_parts(parts)
    
    # Simple type - check if it's a known type
    if type_str in SIMPLE_TYPES:
        return ParsedType(base_types=[type_str], allows_none=False, is_valid=True)
    
    # Unknown type - mark as invalid for isinstance but keep the type
    return ParsedType(base_types=[type_str], allows_none=False, is_valid=False)


def _split_comma_parts(inner: str) -> list[str]:
    """
    Split comma-separated parts handling nested brackets.
    
    Example: "str, dict[str, int], None" -> ["str", "dict[str, int]", "None"]
    """
    parts = []
    current = ""
    depth = 0
    
    for char in inner:
        if char == "[":
            depth += 1
            current += char
        elif char == "]":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += char
    
    if current.strip():
        parts.append(current.strip())
    
    return parts


def _parse_type_parts(parts: list[str]) -> ParsedType:
    """
    Parse a list of union type parts.
    
    Args:
        parts: List like ["str", "int", "None"]
        
    Returns:
        ParsedType with combined information
    """
    base_types = []
    allows_none = False
    all_valid = True
    
    for part in parts:
        part = part.strip()
        
        if part == "None":
            allows_none = True
        elif part in SIMPLE_TYPES:
            base_types.append(part)
        else:
            # Recursively parse complex parts
            inner_parsed = parse_type_hint(part)
            if inner_parsed.allows_none:
                allows_none = True
            base_types.extend(inner_parsed.base_types)
            if not inner_parsed.is_valid:
                all_valid = False
    
    return ParsedType(
        base_types=base_types,
        allows_none=allows_none,
        is_valid=all_valid
    )


def generate_isinstance_expression(parsed: ParsedType, var_name: str = "result") -> str | None:
    """
    Generate an isinstance check expression for a parsed type.
    
    Args:
        parsed: Parsed type information
        var_name: Variable name to check
        
    Returns:
        Expression string like "x is None or isinstance(x, str)" or None if can't generate
    """
    if not parsed.is_valid:
        return None
    
    # Only None allowed
    if not parsed.base_types:
        if parsed.allows_none:
            return f"{var_name} is None"
        return None
    
    # Build the type tuple for isinstance
    if len(parsed.base_types) == 1:
        # Single type - use mapping (handles float -> (int, float))
        type_expr = ISINSTANCE_MAPPING.get(parsed.base_types[0], parsed.base_types[0])
    else:
        # Multiple types - build tuple
        types = []
        for t in parsed.base_types:
            mapped = ISINSTANCE_MAPPING.get(t, t)
            # Handle already-tuple mappings like "(int, float)"
            if mapped.startswith("(") and mapped.endswith(")"):
                # Extract inner types
                inner = mapped[1:-1]
                types.extend(inner.split(", "))
            else:
                types.append(mapped)
        # Deduplicate while preserving order
        seen = set()
        unique_types = []
        for t in types:
            if t not in seen:
                seen.add(t)
                unique_types.append(t)
        type_expr = f"({', '.join(unique_types)})"
    
    isinstance_check = f"isinstance({var_name}, {type_expr})"
    
    # Add None check if needed
    if parsed.allows_none:
        return f"{var_name} is None or {isinstance_check}"
    else:
        return isinstance_check


def generate_type_assertions(return_type: str | None) -> list[str]:
    """
    Generate type-checking assertions based on return type.
    
    Handles complex types safely:
    - Simple types: isinstance checks
    - Union with None: "result is None or isinstance(result, ...)"
    - Union types: isinstance with tuple
    - Containers: container check + element checks if safe
    - Complex/unknown types: falls back to container-only or no assertion
    
    Args:
        return_type: The function's return type annotation
        
    Returns:
        List of assertion code lines (can be empty if type is unknown)
    """
    if not return_type:
        return []
    
    type_str = return_type.strip()
    
    # Handle None type
    if type_str == "None":
        return ["assert result is None"]
    
    # Handle list[X]
    if type_str.startswith("list[") and type_str.endswith("]"):
        return _generate_list_assertions(type_str)
    
    # Handle dict[K, V]
    if type_str.startswith("dict[") and type_str.endswith("]"):
        return _generate_dict_assertions(type_str)
    
    # Handle set[X]
    if type_str.startswith("set[") and type_str.endswith("]"):
        return _generate_set_assertions(type_str)
    
    # Handle tuple[X, ...] - complex, just check container
    if type_str.startswith("tuple[") and type_str.endswith("]"):
        return ["assert isinstance(result, tuple)"]
    
    # Handle union types and simple types
    parsed = parse_type_hint(type_str)
    check_expr = generate_isinstance_expression(parsed)
    
    if check_expr:
        return [f"assert {check_expr}"]
    
    # Unknown type - return empty (better no assertion than wrong assertion)
    return []


def _generate_list_assertions(type_str: str) -> list[str]:
    """
    Generate assertions for list[X] type.
    
    Handles:
    - list[str] -> container + element check
    - list[str | None] -> container + safe element check
    - list[ComplexType] -> container only (fallback)
    """
    inner = type_str[5:-1].strip()  # Extract X from list[X]
    
    assertions = ["assert isinstance(result, list)"]
    
    # Parse inner type
    parsed = parse_type_hint(inner)
    
    # Only add element check if we can do it safely
    if parsed.is_valid and (parsed.base_types or parsed.allows_none):
        element_check = generate_isinstance_expression(parsed, "x")
        if element_check:
            # Use "if result else True" to handle empty lists
            assertions.append(
                f"assert all({element_check} for x in result) if result else True"
            )
    
    return assertions


def _generate_dict_assertions(type_str: str) -> list[str]:
    """
    Generate assertions for dict[K, V] type.
    
    Handles:
    - dict[str, int] -> container + key/value checks
    - dict[str, int | None] -> container + safe checks
    - dict[str, ComplexType] -> container + key check only
    """
    inner = type_str[5:-1]  # Extract "K, V" from dict[K, V]
    
    assertions = ["assert isinstance(result, dict)"]
    
    # Split K, V handling nested brackets
    parts = _split_comma_parts(inner)
    
    if len(parts) >= 2:
        key_type = parts[0].strip()
        # Value could have commas if it's a nested generic, rejoin remaining parts
        value_type = ", ".join(parts[1:]).strip()
        
        # Parse and check key type
        key_parsed = parse_type_hint(key_type)
        if key_parsed.is_valid and key_parsed.base_types:
            key_check = generate_isinstance_expression(key_parsed, "k")
            if key_check:
                assertions.append(
                    f"assert all({key_check} for k in result.keys()) if result else True"
                )
        
        # Parse and check value type
        value_parsed = parse_type_hint(value_type)
        if value_parsed.is_valid and (value_parsed.base_types or value_parsed.allows_none):
            value_check = generate_isinstance_expression(value_parsed, "v")
            if value_check:
                assertions.append(
                    f"assert all({value_check} for v in result.values()) if result else True"
                )
    
    return assertions


def _generate_set_assertions(type_str: str) -> list[str]:
    """
    Generate assertions for set[X] type.
    
    Same logic as list[X].
    """
    inner = type_str[4:-1].strip()  # Extract X from set[X]
    
    assertions = ["assert isinstance(result, set)"]
    
    parsed = parse_type_hint(inner)
    
    if parsed.is_valid and (parsed.base_types or parsed.allows_none):
        element_check = generate_isinstance_expression(parsed, "x")
        if element_check:
            assertions.append(
                f"assert all({element_check} for x in result) if result else True"
            )
    
    return assertions