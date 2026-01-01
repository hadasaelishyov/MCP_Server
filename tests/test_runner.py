"""Tests for the test runner module."""

import pytest
from pytest_pipeline_mcp.core.runner import run_tests, PytestRunner, RunResult


class TestRunnerBasics:
    """Test basic runner functionality."""
    
    def test_run_passing_tests(self):
        """Test runner with all passing tests."""
        source = "def add(a, b): return a + b"
        tests = '''
import pytest
from module import add

def test_add():
    assert add(1, 2) == 3
'''
        result = run_tests(source, tests)
        
        assert result.total == 1
        assert result.passed == 1
        assert result.failed == 0
        assert result.success is True
    
    def test_run_failing_tests(self):
        """Test runner with failing tests."""
        source = "def add(a, b): return a + b"
        tests = '''
import pytest
from module import add

def test_add_wrong():
    assert add(1, 2) == 99
'''
        result = run_tests(source, tests)
        
        assert result.total == 1
        assert result.passed == 0
        assert result.failed == 1
        assert result.success is False
        assert len(result.failed_tests) == 1
        assert result.failed_tests[0]['name'] == 'test_add_wrong'
    
    def test_run_mixed_results(self):
        """Test runner with mixed pass/fail."""
        source = """
def add(a, b): return a + b
def sub(a, b): return a - b
"""
        tests = '''
import pytest
from module import add, sub

def test_add_pass():
    assert add(1, 2) == 3

def test_sub_fail():
    assert sub(5, 3) == 99
'''
        result = run_tests(source, tests)
        
        assert result.total == 2
        assert result.passed == 1
        assert result.failed == 1
        assert result.success is False


class TestModuleDetection:
    """Test module name detection."""
    
    def test_detect_module_name(self):
        """Test module name is detected from imports."""
        tests = '''
import pytest
from calculator import add
'''
        runner = PytestRunner("def add(a,b): return a+b", tests)
        assert runner.module_name == "calculator"
    
    def test_detect_default_module(self):
        """Test default module name when no import found."""
        tests = '''
import pytest

def test_something():
    pass
'''
        runner = PytestRunner("x = 1", tests)
        assert runner.module_name == "module"
    
    def test_skip_standard_imports(self):
        """Test that standard library imports are skipped."""
        tests = '''
import pytest
from typing import List
from collections import defaultdict
from mymodule import func
'''
        runner = PytestRunner("def func(): pass", tests)
        assert runner.module_name == "mymodule"


class TestCoverage:
    """Test coverage measurement."""
    
    def test_coverage_reported(self):
        """Test that coverage is reported."""
        source = """
def add(a, b):
    return a + b
"""
        tests = '''
import pytest
from module import add

def test_add():
    assert add(1, 2) == 3
'''
        result = run_tests(source, tests)
        
        assert result.coverage is not None
        assert result.coverage.percentage == 100.0
    
    def test_partial_coverage(self):
        """Test partial coverage detection."""
        source = """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
        tests = '''
import pytest
from module import add

def test_add():
    assert add(1, 2) == 3
'''
        result = run_tests(source, tests)
        
        assert result.coverage is not None
        # Only add is tested, multiply is not
        assert result.coverage.percentage < 100.0


class TestErrorHandling:
    """Test error handling."""
    
    def test_syntax_error_in_source(self):
        """Test handling of syntax error in source."""
        source = "def broken( return"  # Invalid syntax
        tests = '''
import pytest
from module import broken

def test_broken():
    pass
'''
        result = run_tests(source, tests)
        
        assert result.success is False
        assert result.errors >= 1 or result.error_message is not None
    
    def test_import_error(self):
        """Test handling of import error."""
        source = "def add(a, b): return a + b"
        tests = '''
import pytest
from module import nonexistent_function

def test_something():
    pass
'''
        result = run_tests(source, tests)
        
        assert result.success is False