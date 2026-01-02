"""Extract doctest examples from docstrings and convert them to pytest assertions."""


import ast
import doctest
from dataclasses import dataclass


@dataclass
class DoctestExample:
    """A single doctest example."""
    call: str           # "add(1, 2)"
    expected: str       # "3"
    line_number: int    # Where in docstring


def extract_doctests(docstring: str | None) -> list[DoctestExample]:
    """Extract doctest examples with expected outputs from a docstring."""

    if not docstring:
        return []

    parser = doctest.DocTestParser()
    examples = []

    try:
        parsed = parser.get_examples(docstring)
    except ValueError:
        # Malformed doctest
        return []

    for ex in parsed:
        # ex.source includes trailing newline, strip it
        call = ex.source.rstrip('\n')
        # ex.want is the expected output (empty string if none)
        expected = ex.want.rstrip('\n')

        # Skip examples with no expected output
        if not expected:
            continue

        examples.append(DoctestExample(
            call=call,
            expected=expected,
            line_number=ex.lineno + 1  # Convert to 1-based line numbers
        ))

    return examples


def doctest_to_assertion(example: DoctestExample, function_name: str) -> str | None:
    """Convert a doctest example into a safe pytest assertion when possible."""

    call = example.call
    expected = example.expected

    try:
        expr = ast.parse(call, mode="eval").body
    except SyntaxError:
        return None

    if not isinstance(expr, ast.Call):
        return None

    func = expr.func
    ok = (
        isinstance(func, ast.Name) and func.id == function_name
    ) or (
        isinstance(func, ast.Attribute) and func.attr == function_name
    )

    if not ok:
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
