"""
Doctest Extractor - Parse examples from docstrings.

Extracts >>> examples and their expected outputs.
"""

import ast
from dataclasses import dataclass


@dataclass
class DoctestExample:
    """A single doctest example."""
    call: str           # "add(1, 2)"
    expected: str       # "3"
    line_number: int    # Where in docstring


def extract_doctests(docstring: str | None) -> list[DoctestExample]:
    """
    Extract doctest examples from a docstring.
    
    Looks for patterns like:
        >>> function_call(args)
        expected_result
    
    Args:
        docstring: Function's docstring
        
    Returns:
        List of DoctestExample objects
    """
    if not docstring:
        return []
    
    examples = []
    lines = docstring.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for >>> pattern
        if line.startswith('>>>'):
            call = line[3:].strip()
            
            # Check for multi-line call (ends with continuation)
            while call.endswith('\\') and i + 1 < len(lines):
                i += 1
                call = call[:-1] + lines[i].strip()
            
            # Next non-empty, non->>> line is the expected result
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line and not next_line.startswith('>>>'):
                    expected = next_line
                    examples.append(DoctestExample(
                        call=call,
                        expected=expected,
                        line_number=i
                    ))
                    break
                elif next_line.startswith('>>>'):
                    # No expected value, skip this example
                    i -= 1  # Reprocess this line
                    break
                i += 1
        i += 1
    
    return examples


def doctest_to_assertion(example: DoctestExample, function_name: str) -> str | None:
    """
    Convert a doctest example to a pytest assertion.
    
    Args:
        example: The doctest example
        function_name: Name of the function being tested
        
    Returns:
        Assertion string or None if can't convert
    """
    call = example.call
    expected = example.expected
    
    # Verify the call is for this function
    if not call.startswith(function_name + '('):
        return None
    
    # Handle different expected types
    if expected in ('True', 'False', 'None'):
        return f"assert {call} is {expected}"
    
    # Handle exceptions
    if expected.startswith('Traceback'):
        return None  # Can't easily convert these
    
    # Handle string representation
    if expected.startswith("'") or expected.startswith('"'):
        return f"assert {call} == {expected}"
    
    # Handle numeric and other values
    try:
        # Try to evaluate to check it's a valid literal
        ast.literal_eval(expected)
        return f"assert {call} == {expected}"
    except Exception:
        # Can't safely convert
        return None