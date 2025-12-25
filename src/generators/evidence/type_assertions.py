"""
Type Assertions - Generate assertions based on type hints.

Safe assertions we can make based on return type annotations.
"""


# Map type hints to assertion code
TYPE_ASSERTIONS = {
    "int": "assert isinstance(result, int)",
    "str": "assert isinstance(result, str)",
    "float": "assert isinstance(result, (int, float))",
    "bool": "assert isinstance(result, bool)",
    "list": "assert isinstance(result, list)",
    "dict": "assert isinstance(result, dict)",
    "set": "assert isinstance(result, set)",
    "tuple": "assert isinstance(result, tuple)",
    "None": "assert result is None",
    "bytes": "assert isinstance(result, bytes)",
}

# Container type patterns for deeper assertions
CONTAINER_PATTERNS = {
    "list[int]": [
        "assert isinstance(result, list)",
        "assert all(isinstance(x, int) for x in result)"
    ],
    "list[str]": [
        "assert isinstance(result, list)",
        "assert all(isinstance(x, str) for x in result)"
    ],
    "dict[str, int]": [
        "assert isinstance(result, dict)",
        "assert all(isinstance(k, str) for k in result.keys())",
        "assert all(isinstance(v, int) for v in result.values())"
    ],
    "Optional[int]": [
        "assert result is None or isinstance(result, int)"
    ],
    "Optional[str]": [
        "assert result is None or isinstance(result, str)"
    ],
}


def generate_type_assertions(return_type: str | None) -> list[str]:
    """
    Generate type-checking assertions based on return type.
    
    Args:
        return_type: The function's return type annotation
        
    Returns:
        List of assertion code lines
    """
    if not return_type:
        return []
    
    # Clean up the type string
    clean_type = return_type.strip()
    
    # Check for exact container pattern match
    if clean_type in CONTAINER_PATTERNS:
        return CONTAINER_PATTERNS[clean_type]
    
    # Handle union types (int | None)
    if " | None" in clean_type or "| None" in clean_type:
        base_type = clean_type.replace(" | None", "").replace("| None", "").strip()
        if base_type in TYPE_ASSERTIONS:
            base_assertion = TYPE_ASSERTIONS[base_type].replace(
                "assert isinstance(result, ", 
                "assert result is None or isinstance(result, "
            )
            return [base_assertion]
    
    # Handle Optional[X]
    if clean_type.startswith("Optional["):
        inner = clean_type[9:-1]  # Extract inner type
        if inner in TYPE_ASSERTIONS:
            return [f"assert result is None or isinstance(result, {inner})"]
    
    # Handle list[X]
    if clean_type.startswith("list["):
        inner = clean_type[5:-1]
        return [
            "assert isinstance(result, list)",
            f"assert all(isinstance(x, {inner}) for x in result) if result else True"
        ]
    
    # Check simple types
    # Handle simple type (might be in format "int", "str", etc.)
    base_type = clean_type.split("[")[0]  # Get base type without generics
    if base_type in TYPE_ASSERTIONS:
        return [TYPE_ASSERTIONS[base_type]]
    
    return []
