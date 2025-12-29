"""
Tests for parser parameter kind handling.

Tests cover:
- Positional-only parameters (before /)
- Keyword-only parameters (after *)
- Mixed parameter kinds
- Defaults alignment across all kinds
- *args and **kwargs
"""

import pytest
from src.tools.core.analyzer.parser import parse_code, extract_functions
from src.tools.core.analyzer.models import ParameterInfo


class TestPositionalOnlyParameters:
    """Test positional-only parameters (Python 3.8+)."""
    
    def test_simple_positional_only(self):
        """Test function with positional-only parameters."""
        code = "def func(a, b, /): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        assert len(funcs) == 1
        params = funcs[0].parameters
        
        assert len(params) == 2
        assert params[0].name == "a"
        assert params[0].kind == "positional_only"
        assert params[1].name == "b"
        assert params[1].kind == "positional_only"
    
    def test_positional_only_with_defaults(self):
        """Test positional-only with default values."""
        code = "def func(a, b=1, /): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].name == "a"
        assert params[0].has_default is False
        assert params[0].kind == "positional_only"
        
        assert params[1].name == "b"
        assert params[1].has_default is True
        assert params[1].default_value == "1"
        assert params[1].kind == "positional_only"
    
    def test_positional_only_mixed_with_regular(self):
        """Test positional-only mixed with regular parameters."""
        code = "def func(a, /, b, c): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 3
        assert params[0].name == "a"
        assert params[0].kind == "positional_only"
        assert params[1].name == "b"
        assert params[1].kind == "positional_or_keyword"
        assert params[2].name == "c"
        assert params[2].kind == "positional_or_keyword"


class TestKeywordOnlyParameters:
    """Test keyword-only parameters (after *)."""
    
    def test_keyword_only_with_star(self):
        """Test keyword-only parameters after bare *."""
        code = "def func(*, a, b): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 2
        assert params[0].name == "a"
        assert params[0].kind == "keyword_only"
        assert params[1].name == "b"
        assert params[1].kind == "keyword_only"
    
    def test_keyword_only_with_defaults(self):
        """Test keyword-only with some defaults."""
        code = "def func(*, required, optional=None): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].name == "required"
        assert params[0].has_default is False
        assert params[0].kind == "keyword_only"
        
        assert params[1].name == "optional"
        assert params[1].has_default is True
        assert params[1].default_value == "None"
        assert params[1].kind == "keyword_only"
    
    def test_keyword_only_after_args(self):
        """Test keyword-only after *args."""
        code = "def func(*args, kw_only): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 2
        assert params[0].name == "*args"
        assert params[0].kind == "var_positional"
        assert params[1].name == "kw_only"
        assert params[1].kind == "keyword_only"


class TestAllParameterKinds:
    """Test all parameter kinds together."""
    
    def test_all_kinds_simple(self):
        """Test function with all parameter kinds."""
        code = "def func(pos_only, /, normal, *args, kw_only, **kwargs): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 5
        
        assert params[0].name == "pos_only"
        assert params[0].kind == "positional_only"
        
        assert params[1].name == "normal"
        assert params[1].kind == "positional_or_keyword"
        
        assert params[2].name == "*args"
        assert params[2].kind == "var_positional"
        
        assert params[3].name == "kw_only"
        assert params[3].kind == "keyword_only"
        
        assert params[4].name == "**kwargs"
        assert params[4].kind == "var_keyword"
    
    def test_all_kinds_with_defaults(self):
        """Test all kinds with defaults properly aligned."""
        code = """
def func(a, b=1, /, c=2, d=3, *args, e, f=4, **kwargs):
    pass
"""
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        # pos_only without default
        assert params[0].name == "a"
        assert params[0].kind == "positional_only"
        assert params[0].has_default is False
        
        # pos_only with default
        assert params[1].name == "b"
        assert params[1].kind == "positional_only"
        assert params[1].has_default is True
        assert params[1].default_value == "1"
        
        # regular with defaults
        assert params[2].name == "c"
        assert params[2].kind == "positional_or_keyword"
        assert params[2].has_default is True
        assert params[2].default_value == "2"
        
        assert params[3].name == "d"
        assert params[3].kind == "positional_or_keyword"
        assert params[3].has_default is True
        assert params[3].default_value == "3"
        
        # *args
        assert params[4].name == "*args"
        assert params[4].kind == "var_positional"
        
        # keyword-only without default
        assert params[5].name == "e"
        assert params[5].kind == "keyword_only"
        assert params[5].has_default is False
        
        # keyword-only with default
        assert params[6].name == "f"
        assert params[6].kind == "keyword_only"
        assert params[6].has_default is True
        assert params[6].default_value == "4"
        
        # **kwargs
        assert params[7].name == "**kwargs"
        assert params[7].kind == "var_keyword"
    
    def test_type_hints_on_all_kinds(self):
        """Test type hints are extracted for all parameter kinds."""
        code = """
def func(a: int, /, b: str, *args: tuple, c: float, **kwargs: dict) -> None:
    pass
"""
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].type_hint == "int"
        assert params[0].kind == "positional_only"
        
        assert params[1].type_hint == "str"
        assert params[1].kind == "positional_or_keyword"
        
        assert params[2].type_hint == "tuple"
        assert params[2].kind == "var_positional"
        
        assert params[3].type_hint == "float"
        assert params[3].kind == "keyword_only"
        
        assert params[4].type_hint == "dict"
        assert params[4].kind == "var_keyword"


class TestDefaultsAlignment:
    """Test that defaults are correctly aligned across parameter kinds."""
    
    def test_defaults_only_on_regular(self):
        """Defaults only on regular parameters."""
        code = "def func(a, b, c=1, d=2): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].has_default is False
        assert params[1].has_default is False
        assert params[2].has_default is True
        assert params[2].default_value == "1"
        assert params[3].has_default is True
        assert params[3].default_value == "2"
    
    def test_defaults_across_posonly_and_regular(self):
        """Defaults spanning positional-only and regular."""
        code = "def func(a, b=1, /, c=2): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].name == "a"
        assert params[0].has_default is False
        
        assert params[1].name == "b"
        assert params[1].has_default is True
        assert params[1].default_value == "1"
        
        assert params[2].name == "c"
        assert params[2].has_default is True
        assert params[2].default_value == "2"
    
    def test_kwonly_defaults_independent(self):
        """Keyword-only defaults are independent from positional defaults."""
        code = "def func(a, b=1, *, c, d=2): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].name == "a"
        assert params[0].has_default is False
        
        assert params[1].name == "b"
        assert params[1].has_default is True
        
        assert params[2].name == "c"
        assert params[2].has_default is False  # kw-only without default
        
        assert params[3].name == "d"
        assert params[3].has_default is True
        assert params[3].default_value == "2"


class TestEdgeCases:
    """Test edge cases in parameter parsing."""
    
    def test_only_kwargs(self):
        """Function with only **kwargs."""
        code = "def func(**kwargs): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 1
        assert params[0].name == "**kwargs"
        assert params[0].kind == "var_keyword"
    
    def test_only_args(self):
        """Function with only *args."""
        code = "def func(*args): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 1
        assert params[0].name == "*args"
        assert params[0].kind == "var_positional"
    
    def test_no_parameters(self):
        """Function with no parameters."""
        code = "def func(): pass"
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert len(params) == 0
    
    def test_self_parameter(self):
        """Method with self parameter."""
        code = """
class MyClass:
    def method(self, a, /, b, *, c):
        pass
"""
        tree = parse_code(code)
        from src.tools.core.analyzer.parser import extract_classes
        classes = extract_classes(tree)
        
        method = classes[0].methods[0]
        params = method.parameters
        
        assert params[0].name == "self"
        assert params[0].kind == "positional_only"
        
        assert params[1].name == "a"
        assert params[1].kind == "positional_only"
        
        assert params[2].name == "b"
        assert params[2].kind == "positional_or_keyword"
        
        assert params[3].name == "c"
        assert params[3].kind == "keyword_only"
    
    def test_complex_defaults(self):
        """Test various default value types."""
        code = '''
def func(
    a=[],
    b={},
    c=(),
    d=None,
    e="string",
    f=42,
    g=3.14
): pass
'''
        tree = parse_code(code)
        funcs = extract_functions(tree)
        
        params = funcs[0].parameters
        
        assert params[0].default_value == "[]"
        assert params[1].default_value == "{}"
        assert params[2].default_value == "()"
        assert params[3].default_value == "None"
        assert params[4].default_value == "'string'"
        assert params[5].default_value == "42"
        assert params[6].default_value == "3.14"
