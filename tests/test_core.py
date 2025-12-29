"""Tests for core analyzer."""

import pytest
from src.tools.core.analyzer import analyze_code
from src.tools.core.analyzer.parser import parse_code, extract_functions, extract_classes


class TestParser:
    """Test the parser module."""

    def test_parse_valid_code(self):
        """Test parsing valid Python code."""
        code = "def add(a, b): return a + b"
        tree = parse_code(code)
        assert tree is not None

    def test_parse_invalid_code(self):
        """Test parsing invalid Python code."""
        code = "def add(a, b) return a + b"  # Missing colon
        tree = parse_code(code)
        assert tree is None

    def test_extract_function(self):
        """Test extracting a simple function."""
        code = "def greet(name: str) -> str: return name"
        tree = parse_code(code)
        functions = extract_functions(tree)
        
        assert len(functions) == 1
        assert functions[0].name == "greet"
        assert functions[0].return_type == "str"
        assert len(functions[0].parameters) == 1
        assert functions[0].parameters[0].name == "name"
        assert functions[0].parameters[0].type_hint == "str"

    def test_extract_class(self):
        """Test extracting a class with methods."""
        code = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
"""
        tree = parse_code(code)
        classes = extract_classes(tree)
        
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert len(classes[0].methods) == 1
        assert classes[0].methods[0].name == "add"


class TestAnalyzer:
    """Test the main analyzer."""

    def test_analyze_valid_code(self):
        """Test analyzing valid code."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        result = analyze_code(code)
        
        assert result.valid is True
        assert result.error is None
        assert len(result.functions) == 1

    def test_analyze_invalid_syntax(self):
        """Test analyzing code with syntax error."""
        code = "def broken( return"
        result = analyze_code(code)
        
        assert result.valid is False
        assert result.error is not None
        assert "Syntax error" in result.error

    def test_warnings_for_missing_type_hints(self):
        """Test that missing type hints generate warnings."""
        code = """
def process(data):
    return data
"""
        result = analyze_code(code)
        
        assert result.valid is True
        assert any("missing" in w.lower() and "type hint" in w.lower() 
                   for w in result.warnings)

    def test_complexity_calculation(self):
        """Test complexity is calculated correctly."""
        code = """
def simple():
    return 1

def complex_func(data):
    if data:
        for item in data:
            if item.valid:
                return item
    return None
"""
        result = analyze_code(code)
        
        assert len(result.functions) == 2
        # simple() has complexity 1
        assert result.functions[0].complexity == 1
        # complex_func has complexity 4 (1 base + if + for + if)
        assert result.functions[1].complexity == 4

    def test_statistics(self):
        """Test statistics are calculated."""
        code = """
def func1(a: int) -> int:
    return a

def func2(b):
    return b
"""
        result = analyze_code(code)
        
        assert result.total_functions == 2
        assert result.type_hint_coverage == 50.0  # 1 of 2 fully typed