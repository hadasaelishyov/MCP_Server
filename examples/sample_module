"""
Example module for testing pytest-generator-mcp.
"""

from typing import Optional


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def greet(name: str, greeting: str = "Hello") -> str:
    """Generate a greeting message."""
    return f"{greeting}, {name}!"


def find_max(numbers: list[int]) -> Optional[int]:
    """Find the maximum number in a list."""
    if not numbers:
        return None
    return max(numbers)


# Function without type hints - should trigger warning
def process_data(data):
    """Process data without type hints."""
    if data is None:
        return []
    return [item.strip() for item in data if item]