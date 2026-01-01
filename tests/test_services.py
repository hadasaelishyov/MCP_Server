"""
Tests for the Service Layer.

These tests demonstrate the key benefits:
- Services tested WITHOUT MCP infrastructure
- Clean mocking and dependency injection
- Comprehensive coverage of success and failure paths
"""

import pytest
from unittest.mock import Mock
from pathlib import Path
import tempfile
import os

from pytest_pipeline_mcp.services import (
    # Base
    ServiceResult,
    ServiceError,
    ErrorCode,
    # Code loading
    CodeLoader,
    LoadedCode,
    # Services
    AnalysisService,
    GenerationService,
    ExecutionService,
    FixingService,
)


# =============================================================================
# ServiceResult Tests
# =============================================================================

class TestServiceResult:
    """Tests for the ServiceResult pattern."""
    
    def test_ok_creates_success_result(self):
        """Test creating a successful result."""
        result = ServiceResult.ok({"key": "value"})
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_fail_creates_failure_result(self):
        """Test creating a failed result."""
        result = ServiceResult.fail(
            ErrorCode.VALIDATION_ERROR,
            "Something went wrong",
            details={"field": "name"}
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error is not None
        assert result.error.code == ErrorCode.VALIDATION_ERROR
        assert result.error.message == "Something went wrong"
        assert result.error.details == {"field": "name"}
    
    def test_map_transforms_success(self):
        """Test map transforms data on success."""
        result = ServiceResult.ok(5)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.success is True
        assert mapped.data == 10
    
    def test_map_preserves_failure(self):
        """Test map preserves error on failure."""
        result = ServiceResult.fail(ErrorCode.INTERNAL_ERROR, "error")
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.success is False
        assert mapped.error.message == "error"
    
    def test_unwrap_returns_data_on_success(self):
        """Test unwrap returns data when successful."""
        result = ServiceResult.ok("hello")
        assert result.unwrap() == "hello"
    
    def test_unwrap_raises_on_failure(self):
        """Test unwrap raises ValueError on failure."""
        result = ServiceResult.fail(ErrorCode.INTERNAL_ERROR, "error")
        
        with pytest.raises(ValueError, match="error"):
            result.unwrap()
    
    def test_unwrap_or_returns_data_on_success(self):
        """Test unwrap_or returns data when successful."""
        result = ServiceResult.ok("hello")
        assert result.unwrap_or("default") == "hello"
    
    def test_unwrap_or_returns_default_on_failure(self):
        """Test unwrap_or returns default on failure."""
        result = ServiceResult.fail(ErrorCode.INTERNAL_ERROR, "error")
        assert result.unwrap_or("default") == "default"
    
    def test_error_to_dict(self):
        """Test error serialization."""
        result = ServiceResult.fail(
            ErrorCode.FILE_NOT_FOUND,
            "File missing",
            details={"path": "/test.py"}
        )
        
        error_dict = result.error.to_dict()
        
        assert error_dict["code"] == "file_not_found"
        assert error_dict["message"] == "File missing"
        assert error_dict["details"]["path"] == "/test.py"


# =============================================================================
# CodeLoader Tests
# =============================================================================

class TestCodeLoader:
    """Tests for CodeLoader."""
    
    def test_load_from_string(self):
        """Test loading code from direct string input."""
        loader = CodeLoader()
        
        result = loader.load(code="def add(a, b): return a + b")
        
        assert result.success is True
        assert result.data.content == "def add(a, b): return a + b"
        assert result.data.module_name == "module"
        assert result.data.source_path is None
    
    def test_load_rejects_too_large_code(self):
        """Test that oversized code is rejected."""
        loader = CodeLoader(max_size=100)
        
        large_code = "x = 1\n" * 50  # More than 100 bytes
        result = loader.load(code=large_code)
        
        assert result.success is False
        assert result.error.code == ErrorCode.FILE_TOO_LARGE
    
    def test_load_requires_code_or_file(self):
        """Test that either code or file_path is required."""
        loader = CodeLoader()
        
        result = loader.load()  # Neither provided
        
        assert result.success is False
        assert result.error.code == ErrorCode.MISSING_INPUT
    
    def test_load_validates_extension(self):
        """Test that only .py files are allowed."""
        loader = CodeLoader()
        
        result = loader.load(file_path="test.txt")
        
        assert result.success is False
        assert result.error.code == ErrorCode.INVALID_EXTENSION
    
    def test_load_from_real_file(self):
        """Test loading from an actual file."""
        loader = CodeLoader()
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write("def hello(): pass")
            temp_path = f.name
        
        try:
            result = loader.load(file_path=temp_path)
            
            assert result.success is True
            assert result.data.content == "def hello(): pass"
            assert result.data.source_path == temp_path
        finally:
            os.unlink(temp_path)
    
    def test_load_file_not_found(self):
        """Test error when file doesn't exist."""
        loader = CodeLoader()
        
        result = loader.load(file_path="/nonexistent/file.py")
        
        assert result.success is False
        assert result.error.code == ErrorCode.FILE_NOT_FOUND
    
    def test_load_falls_back_to_code(self):
        """Test fallback to code when file not found."""
        loader = CodeLoader()
        
        result = loader.load(
            file_path="/nonexistent/file.py",
            code="def fallback(): pass"
        )
        
        assert result.success is True
        assert result.data.content == "def fallback(): pass"
        assert result.data.module_name == "file"
    
    def test_extract_module_name(self):
        """Test module name extraction from path."""
        loader = CodeLoader()
        
        assert loader._extract_module_name("test.py") == "test"
        assert loader._extract_module_name("/path/to/module.py") == "module"
        assert loader._extract_module_name("calculator.py") == "calculator"


# =============================================================================
# AnalysisService Tests
# =============================================================================

class TestAnalysisService:
    """Tests for AnalysisService."""
    
    def test_analyze_simple_function(self):
        """Test analyzing a simple function."""
        service = AnalysisService()
        
        result = service.analyze(code="def add(a: int, b: int) -> int:\n    return a + b")
        
        assert result.success is True
        assert result.data.valid is True
        assert len(result.data.functions) == 1
        assert result.data.functions[0].name == "add"
    
    def test_analyze_class(self):
        """Test analyzing a class."""
        service = AnalysisService()
        
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        result = service.analyze(code=code)
        
        assert result.success is True
        assert len(result.data.classes) == 1
        assert result.data.classes[0].name == "Calculator"
    
    def test_analyze_syntax_error(self):
        """Test that syntax errors are caught."""
        service = AnalysisService()
        
        result = service.analyze(code="def broken(")
        
        assert result.success is False
        assert result.error.code == ErrorCode.SYNTAX_ERROR
    
    def test_analyze_empty_code(self):
        """Test analyzing empty code."""
        service = AnalysisService()
        
        result = service.analyze(code="")
        
        assert result.success is False
    
    def test_analyze_with_custom_loader(self):
        """Test injection of custom CodeLoader."""
        mock_loader = Mock(spec=CodeLoader)
        mock_loader.load.return_value = ServiceResult.ok(
            LoadedCode(content="def test(): pass", module_name="test")
        )
        
        service = AnalysisService(code_loader=mock_loader)
        result = service.analyze(code="ignored")
        
        assert result.success is True
        mock_loader.load.assert_called_once()
    
    def test_analyze_with_metadata(self):
        """Test analyze_with_metadata returns both analysis and load info."""
        service = AnalysisService()
        
        result = service.analyze_with_metadata(code="def test(): pass")
        
        assert result.success is True
        analysis, loaded = result.data
        assert analysis.valid is True
        assert loaded.module_name == "module"


# =============================================================================
# GenerationService Tests
# =============================================================================

class TestGenerationService:
    """Tests for GenerationService."""
    
    def test_generate_template_tests(self):
        """Test generating template-based tests."""
        service = GenerationService()
        
        code = "def multiply(a: int, b: int) -> int:\n    return a * b"
        result = service.generate(code=code)
        
        assert result.success is True
        assert result.data.metadata.mode == "Template"
        assert len(result.data.tests.test_cases) > 0
        assert "def test_multiply" in result.data.tests.to_code()
    
    def test_generate_code_only(self):
        """Test generate_code_only returns just the code string."""
        service = GenerationService()
        
        result = service.generate_code_only(code="def add(a, b): return a + b")
        
        assert result.success is True
        assert isinstance(result.data, str)
        assert "def test_add" in result.data
    
    def test_generate_with_doctest(self):
        """Test that doctests are extracted."""
        service = GenerationService()
        
        code = '''
def add(a, b):
    """Add two numbers.
    
    >>> add(1, 2)
    3
    """
    return a + b
'''
        result = service.generate(code=code)
        
        assert result.success is True
        test_code = result.data.tests.to_code()
        assert "assert add(1, 2) == 3" in test_code
    
    def test_generate_saves_to_file(self):
        """Test saving generated tests to file."""
        service = GenerationService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.py"
            
            result = service.generate(
                code="def add(a, b): return a + b",
                output_path=str(output_path)
            )
            
            assert result.success is True
            assert result.data.metadata.saved_to == str(output_path)
            assert output_path.exists()
            assert "def test_add" in output_path.read_text()
    
    def test_generate_handles_syntax_error(self):
        """Test that syntax errors are propagated."""
        service = GenerationService()
        
        result = service.generate(code="def broken(")
        
        assert result.success is False
        assert "Cannot generate tests" in result.error.message


# =============================================================================
# ExecutionService Tests
# =============================================================================

class TestExecutionService:
    """Tests for ExecutionService."""
    
    def test_run_validates_source_code(self):
        """Test that source_code is required."""
        service = ExecutionService()
        
        result = service.run(source_code="", test_code="def test(): pass")
        
        assert result.success is False
        assert result.error.code == ErrorCode.MISSING_INPUT
        assert "source_code" in result.error.message
    
    def test_run_validates_test_code(self):
        """Test that test_code is required."""
        service = ExecutionService()
        
        result = service.run(source_code="def add(): pass", test_code="")
        
        assert result.success is False
        assert result.error.code == ErrorCode.MISSING_INPUT
        assert "test_code" in result.error.message
    
    def test_run_passing_tests(self):
        """Test running passing tests."""
        service = ExecutionService()
        
        source = "def add(a, b): return a + b"
        test = "from module import add\ndef test_add(): assert add(1, 2) == 3"
        
        result = service.run(source_code=source, test_code=test)
        
        assert result.success is True
        assert result.data.success is True
        assert result.data.passed >= 1
    
    def test_run_failing_tests(self):
        """Test running failing tests."""
        service = ExecutionService()
        
        source = "def add(a, b): return a - b"  # Bug!
        test = "from module import add\ndef test_add(): assert add(1, 2) == 3"
        
        result = service.run(source_code=source, test_code=test)
        
        assert result.success is True  # Service succeeded
        assert result.data.success is False  # But tests failed
        assert result.data.failed >= 1
    
    def test_run_and_summarize(self):
        """Test run_and_summarize returns dict."""
        service = ExecutionService()
        
        source = "def add(a, b): return a + b"
        test = "from module import add\ndef test_add(): assert add(1, 2) == 3"
        
        result = service.run_and_summarize(source_code=source, test_code=test)
        
        assert result.success is True
        assert isinstance(result.data, dict)
        assert "summary" in result.data


# =============================================================================
# FixingService Tests
# =============================================================================

class TestFixingService:
    """Tests for FixingService."""
    
    def test_fix_validates_source_code(self):
        """Test that source_code is required."""
        service = FixingService()
        
        result = service.fix(source_code="", test_code="def test(): pass")
        
        assert result.success is False
        assert result.error.code == ErrorCode.MISSING_INPUT
    
    def test_fix_validates_test_code(self):
        """Test that test_code is required."""
        service = FixingService()
        
        result = service.fix(source_code="def add(): pass", test_code="")
        
        assert result.success is False
        assert result.error.code == ErrorCode.MISSING_INPUT
    
    def test_fix_already_passing(self):
        """Test fix when tests already pass."""
        service = FixingService()
        
        source = "def add(a, b): return a + b"
        test = "from module import add\ndef test_add(): assert add(1, 2) == 3"
        
        result = service.fix(source_code=source, test_code=test)
        
        assert result.success is True
        assert result.data.success is True
        assert result.data.fixed_code == source


# =============================================================================
# Integration Tests
# =============================================================================

class TestServiceIntegration:
    """Integration tests showing services working together."""
    
    def test_analyze_then_generate_pipeline(self):
        """Test the analyze → generate pipeline."""
        code = '''
def calculate_area(length: float, width: float) -> float:
    """Calculate rectangle area.
    
    >>> calculate_area(5.0, 3.0)
    15.0
    """
    return length * width
'''
        
        # Step 1: Analyze
        analysis_service = AnalysisService()
        analyze_result = analysis_service.analyze(code=code)
        
        assert analyze_result.success is True
        assert len(analyze_result.data.functions) == 1
        
        # Step 2: Generate
        generation_service = GenerationService()
        generate_result = generation_service.generate(code=code)
        
        assert generate_result.success is True
        assert "test_calculate_area" in generate_result.data.tests.to_code()
        assert "15.0" in generate_result.data.tests.to_code()
    
    def test_generate_then_run_pipeline(self):
        """Test the generate → run pipeline."""
        source = '''
def greet(name: str) -> str:
    """Return a greeting.
    
    >>> greet("World")
    'Hello, World!'
    """
    return f"Hello, {name}!"
'''
        
        # Generate tests
        gen_service = GenerationService()
        gen_result = gen_service.generate(code=source)
        
        assert gen_result.success is True
        
        # Run tests
        exec_service = ExecutionService()
        run_result = exec_service.run(
            source_code=source,
            test_code=gen_result.data.tests.to_code()
        )
        
        assert run_result.success is True
        assert run_result.data.success is True
    
    def test_shared_code_loader(self):
        """Test that services can share a CodeLoader."""
        loader = CodeLoader(max_size=500)
        
        analysis = AnalysisService(code_loader=loader)
        generation = GenerationService(code_loader=loader)
        
        code = "def test(): pass"
        
        assert analysis.analyze(code=code).success is True
        assert generation.generate(code=code).success is True
