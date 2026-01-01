"""
Tests for doctest_extractor module.
"""

import unittest
from pytest_pipeline_mcp.core.generators.extractors.doctest_extractor import DoctestExample, extract_doctests, doctest_to_assertion


class TestExtractDoctests(unittest.TestCase):
    """Tests for extract_doctests function."""
    
    def test_empty_docstring(self):
        """Should return empty list for None or empty docstring."""
        self.assertEqual(extract_doctests(None), [])
        self.assertEqual(extract_doctests(""), [])
    
    def test_simple_example(self):
        """Should extract a simple single-line example."""
        docstring = '''
        Example:
            >>> add(1, 2)
            3
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].call, "add(1, 2)")
        self.assertEqual(examples[0].expected, "3")
    
    def test_multiple_examples(self):
        """Should extract multiple examples from one docstring."""
        docstring = '''
        Examples:
            >>> add(1, 2)
            3
            >>> add(0, 0)
            0
            >>> add(-1, 1)
            0
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 3)
        self.assertEqual(examples[0].call, "add(1, 2)")
        self.assertEqual(examples[1].call, "add(0, 0)")
        self.assertEqual(examples[2].call, "add(-1, 1)")
    
    def test_multiline_example_with_continuation(self):
        """Should handle multi-line examples using ... continuation."""
        docstring = '''
        Example with multi-line input:
            >>> result = {
            ...     'a': 1,
            ...     'b': 2,
            ... }
            >>> result
            {'a': 1, 'b': 2}
        '''
        examples = extract_doctests(docstring)
        # First example has no output (assignment), second shows result
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].call, "result")
        self.assertEqual(examples[0].expected, "{'a': 1, 'b': 2}")
    
    def test_multiline_function_call(self):
        """Should handle function calls split across multiple lines."""
        docstring = '''
        Multi-line function call:
            >>> long_function_name(
            ...     arg1="hello",
            ...     arg2="world",
            ... )
            'hello world'
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 1)
        expected_call = 'long_function_name(\n    arg1="hello",\n    arg2="world",\n)'
        self.assertEqual(examples[0].call, expected_call)
        self.assertEqual(examples[0].expected, "'hello world'")
    
    def test_multiline_expected_output(self):
        """Should handle expected output that spans multiple lines."""
        docstring = '''
        Multi-line output:
            >>> get_multiline()
            'line1
            line2
            line3'
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].call, "get_multiline()")
        self.assertIn("line1", examples[0].expected)
        self.assertIn("line2", examples[0].expected)
    
    def test_list_comprehension(self):
        """Should handle list comprehensions correctly."""
        docstring = '''
        List comprehension example:
            >>> [x * 2 for x in range(3)]
            [0, 2, 4]
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].call, "[x * 2 for x in range(3)]")
        self.assertEqual(examples[0].expected, "[0, 2, 4]")
    
    def test_example_without_output_skipped(self):
        """Examples without expected output should be skipped."""
        docstring = '''
        Setup without checking output:
            >>> x = 5
            >>> x + 1
            6
        '''
        examples = extract_doctests(docstring)
        # Only the second example has expected output
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].call, "x + 1")
        self.assertEqual(examples[0].expected, "6")
    
    def test_string_expected(self):
        """Should handle string expected values."""
        docstring = '''
            >>> greet("world")
            'Hello, world!'
        '''
        examples = extract_doctests(docstring)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].expected, "'Hello, world!'")


class TestDoctestToAssertion(unittest.TestCase):
    """Tests for doctest_to_assertion function."""
    
    def test_simple_numeric_assertion(self):
        """Should convert simple numeric comparison."""
        example = DoctestExample(call="add(1, 2)", expected="3", line_number=1)
        result = doctest_to_assertion(example, "add")
        self.assertEqual(result, "assert add(1, 2) == 3")
    
    def test_boolean_assertion_uses_is(self):
        """Should use 'is' for True/False/None."""
        example = DoctestExample(call="is_valid(x)", expected="True", line_number=1)
        result = doctest_to_assertion(example, "is_valid")
        self.assertEqual(result, "assert is_valid(x) is True")
        
        example = DoctestExample(call="get_none()", expected="None", line_number=1)
        result = doctest_to_assertion(example, "get_none")
        self.assertEqual(result, "assert get_none() is None")
    
    def test_string_assertion(self):
        """Should handle string expected values."""
        example = DoctestExample(call="greet('Bob')", expected="'Hello Bob'", line_number=1)
        result = doctest_to_assertion(example, "greet")
        self.assertEqual(result, "assert greet('Bob') == 'Hello Bob'")
    
    def test_wrong_function_returns_none(self):
        """Should return None if call doesn't match function name."""
        example = DoctestExample(call="other_func(1)", expected="1", line_number=1)
        result = doctest_to_assertion(example, "my_func")
        self.assertIsNone(result)
    
    def test_traceback_returns_none(self):
        """Should return None for exception examples."""
        example = DoctestExample(
            call="bad_call()", 
            expected="Traceback (most recent call last):", 
            line_number=1
        )
        result = doctest_to_assertion(example, "bad_call")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
