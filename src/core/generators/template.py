"""
Template Generator - Main test generation engine.

Combines Layer 1 (basic templates) + Layer 2 (evidence-based enrichment).
"""

from ..analyzer.models import AnalysisResult, ClassInfo, FunctionInfo
from .base import GeneratedTest, GeneratedTestCase, TestGeneratorBase
from .extractors.boundary_values import generate_boundary_values, get_default_value
from .extractors.doctest_extractor import doctest_to_assertion, extract_doctests
from .extractors.exception_detector import detect_exceptions, generate_exception_test
from .extractors.type_assertions import generate_type_assertions


class TemplateGenerator(TestGeneratorBase):
    """
    Template-based test generator.
    
    Layer 1: Basic smoke tests (always generated)
    Layer 2: Evidence-based enrichment (when signals available)
    """

    def __init__(self, source_code: str = ""):
        """
        Initialize generator.
        
        Args:
            source_code: Original source code (needed for exception detection)
        """
        self.source_code = source_code

    def generate_for_function(
        self,
        func: FunctionInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate test cases for a single function."""
        tests = []

        # Skip private/magic methods
        if func.name.startswith('_'):
            return tests

        # Layer 1: Basic smoke test
        tests.append(self._generate_basic_test(func))

        # Layer 2: Evidence-based tests

        # From doctests
        doctest_cases = self._generate_from_doctests(func)
        tests.extend(doctest_cases)

        # From type hints
        if func.return_type:
            type_test = self._generate_type_test(func)
            if type_test:
                tests.append(type_test)

        # From exceptions
        exception_tests = self._generate_exception_tests(func)
        tests.extend(exception_tests)

        # Edge cases from boundary values
        if include_edge_cases:
            boundary_tests = self._generate_boundary_tests(func)
            tests.extend(boundary_tests)

        # Naming heuristics (is_*, has_* → boolean tests)
        heuristic_test = self._generate_from_naming(func)
        if heuristic_test:
            tests.append(heuristic_test)

        return tests

    def generate_for_class(
        self,
        cls: ClassInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate test cases for a class."""
        tests = []

        # Test class instantiation
        tests.append(self._generate_class_init_test(cls))

        # Test each public method
        for method in cls.methods:
            if not method.name.startswith('_') or method.name == '__init__':
                if method.name != '__init__':
                    method_tests = self._generate_method_tests(cls, method, include_edge_cases)
                    tests.extend(method_tests)

        return tests

    # =========================================================================
    # Layer 1: Basic Tests
    # =========================================================================

    def _generate_basic_test(self, func: FunctionInfo) -> GeneratedTestCase:
        """Generate basic smoke test - verifies function runs without error."""
        body = []

        # Build function call with default values
        params = self._build_param_assignments(func)
        body.extend(params)

        # Call function
        call = self._build_function_call(func)
        body.append(f"result = {call}")

        # Basic assertion
        body.append("assert result is not None or result == 0 or result == '' or result == [] or result == {}")

        return GeneratedTestCase(
            name=f"test_{func.name}_basic",
            description=f"Test {func.name} executes without error.",
            body=body,
            evidence_source="template"
        )

    def _generate_class_init_test(self, cls: ClassInfo) -> GeneratedTestCase:
        """Generate test for class instantiation."""
        # Find __init__ to get parameters
        init_method = None
        for method in cls.methods:
            if method.name == '__init__':
                init_method = method
                break

        body = []

        if init_method:
            params = self._build_param_assignments(init_method, skip_self=True)
            body.extend(params)

            # Get param names for call
            param_names = [
                p.name for p in init_method.parameters
                if p.name not in ('self', 'cls')
            ]
            if param_names:
                body.append(f"instance = {cls.name}({', '.join(param_names)})")
            else:
                body.append(f"instance = {cls.name}()")
        else:
            body.append(f"instance = {cls.name}()")

        body.append("assert instance is not None")

        return GeneratedTestCase(
            name=f"test_{cls.name.lower()}_creation",
            description=f"Test {cls.name} can be instantiated.",
            body=body,
            evidence_source="template"
        )

    def _generate_method_tests(
        self,
        cls: ClassInfo,
        method: FunctionInfo,
        include_edge_cases: bool
    ) -> list[GeneratedTestCase]:
        """Generate tests for a class method."""
        tests = []

        body = []
        body.append(f"instance = {cls.name}()")

        # Build method call
        params = self._build_param_assignments(method, skip_self=True)
        body.extend(params)

        param_names = [
            p.name for p in method.parameters
            if p.name not in ('self', 'cls')
        ]

        if param_names:
            call = f"instance.{method.name}({', '.join(param_names)})"
        else:
            call = f"instance.{method.name}()"

        body.append(f"result = {call}")
        body.append("assert result is not None or result == 0 or result == '' or result == []")

        tests.append(GeneratedTestCase(
            name=f"test_{cls.name.lower()}_{method.name}",
            description=f"Test {cls.name}.{method.name}() method.",
            body=body,
            evidence_source="template"
        ))

        return tests

    # =========================================================================
    # Layer 2: Evidence-Based Tests
    # =========================================================================

    def _generate_from_doctests(self, func: FunctionInfo) -> list[GeneratedTestCase]:
        """Generate tests from docstring examples."""
        if not func.docstring:
            return []

        tests = []
        examples = extract_doctests(func.docstring)

        for i, example in enumerate(examples):
            assertion = doctest_to_assertion(example, func.name)
            if assertion:
                test_name = f"test_{func.name}_doctest_{i + 1}"
                tests.append(GeneratedTestCase(
                    name=test_name,
                    description=f"Test {func.name} with documented example.",
                    body=[assertion],
                    evidence_source="doctest"
                ))

        return tests

    def _generate_type_test(self, func: FunctionInfo) -> GeneratedTestCase | None:
        """Generate test that verifies return type."""
        assertions = generate_type_assertions(func.return_type)

        if not assertions:
            return None

        body = []

        # Build call
        params = self._build_param_assignments(func)
        body.extend(params)

        call = self._build_function_call(func)
        body.append(f"result = {call}")

        # Add type assertions
        body.extend(assertions)

        return GeneratedTestCase(
            name=f"test_{func.name}_return_type",
            description=f"Test {func.name} returns correct type.",
            body=body,
            evidence_source="type_hint"
        )

    def _generate_exception_tests(self, func: FunctionInfo) -> list[GeneratedTestCase]:
        """Generate tests for detected exceptions."""
        if not self.source_code:
            return []

        tests = []
        exceptions = detect_exceptions(self.source_code, func.name)

        for i, exc in enumerate(exceptions):
            # Build param values
            param_values = self._build_param_values(func)

            lines = generate_exception_test(
                func_name=func.name,
                exception=exc,
                param_values=param_values
            )

            test_name = f"test_{func.name}_raises_{exc.exception_type.lower()}"
            if i > 0:
                test_name += f"_{i + 1}"

            tests.append(GeneratedTestCase(
                name=test_name,
                description=f"Test {func.name} raises {exc.exception_type}.",
                body=lines,
                evidence_source="exception"
            ))

        return tests

    def _generate_boundary_tests(self, func: FunctionInfo) -> list[GeneratedTestCase]:
        """Generate tests with boundary values."""
        tests = []

        # Find parameters with type hints
        typed_params = [
            p for p in func.parameters
            if p.type_hint and p.name not in ('self', 'cls')
        ]

        if not typed_params:
            return tests

        # Generate one boundary test per parameter (first typed param only to avoid explosion)
        param = typed_params[0]
        boundaries = generate_boundary_values(param.type_hint)

        # Pick interesting boundaries (not all - avoid test explosion)
        interesting = [b for b in boundaries if b.category in ('zero', 'empty', 'negative')][:2]

        for boundary in interesting:
            body = []

            # Set up parameters
            for p in func.parameters:
                if p.name in ('self', 'cls'):
                    continue
                if p.name == param.name:
                    body.append(f"{p.name} = {boundary.value}")
                else:
                    body.append(f"{p.name} = {get_default_value(p.type_hint)}")

            call = self._build_function_call(func)
            body.append(f"result = {call}")
            body.append("# Verify function handles boundary value")
            body.append("assert result is not None or result == 0 or result == '' or result == [] or result is False")

            test_name = f"test_{func.name}_with_{boundary.description.replace(' ', '_')}"
            tests.append(GeneratedTestCase(
                name=test_name,
                description=f"Test {func.name} with {boundary.description}.",
                body=body,
                evidence_source="boundary"
            ))

        return tests

    def _generate_from_naming(self, func: FunctionInfo) -> GeneratedTestCase | None:
        """Generate tests based on naming conventions."""
        name = func.name.lower()

        # is_* or has_* → should return boolean
        if name.startswith('is_') or name.startswith('has_'):
            body = []
            params = self._build_param_assignments(func)
            body.extend(params)

            call = self._build_function_call(func)
            body.append(f"result = {call}")
            body.append("assert isinstance(result, bool), f'Expected bool, got {type(result)}'")

            return GeneratedTestCase(
                name=f"test_{func.name}_returns_boolean",
                description=f"Test {func.name} returns boolean (naming convention).",
                body=body,
                evidence_source="naming_heuristic"
            )

        # get_* → should not return None (usually)
        if name.startswith('get_'):
            body = []
            params = self._build_param_assignments(func)
            body.extend(params)

            call = self._build_function_call(func)
            body.append(f"result = {call}")
            body.append("# get_* functions typically return a value")
            body.append("# Note: May return None if not found - adjust as needed")

            return GeneratedTestCase(
                name=f"test_{func.name}_returns_value",
                description=f"Test {func.name} returns a value.",
                body=body,
                evidence_source="naming_heuristic"
            )

        return None

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_param_assignments(
        self,
        func: FunctionInfo,
        skip_self: bool = False
    ) -> list[str]:
        """Build parameter assignment lines."""
        lines = []

        for param in func.parameters:
            if param.name in ('self', 'cls'):
                continue

            if param.has_default and param.default_value:
                value = param.default_value
            else:
                value = get_default_value(param.type_hint)

            lines.append(f"{param.name} = {value}")

        return lines

    def _build_function_call(self, func: FunctionInfo) -> str:
        """Build function call string."""
        param_names = [
            p.name for p in func.parameters
            if p.name not in ('self', 'cls')
        ]

        if param_names:
            return f"{func.name}({', '.join(param_names)})"
        return f"{func.name}()"

    def _build_param_values(self, func: FunctionInfo) -> str:
        """Build comma-separated param values for function call."""
        values = []
        for param in func.parameters:
            if param.name in ('self', 'cls'):
                continue
            values.append(get_default_value(param.type_hint))
        return ", ".join(values)


def generate_tests(
    analysis: AnalysisResult,
    source_code: str,
    module_name: str = "module",
    include_edge_cases: bool = True
) -> GeneratedTest:
    """
    Main entry point - generate tests from analysis result.
    
    Args:
        analysis: Result from analyze_code()
        source_code: Original source code
        module_name: Name for imports
        include_edge_cases: Whether to generate boundary tests
        
    Returns:
        GeneratedTest with complete test code
    """
    generator = TemplateGenerator(source_code=source_code)

    test_cases = []
    imports = []
    warnings = []

    # Generate for functions
    for func in analysis.functions:
        imports.append(func.name)
        func_tests = generator.generate_for_function(func, include_edge_cases)
        test_cases.extend(func_tests)

    # Generate for classes
    for cls in analysis.classes:
        imports.append(cls.name)
        class_tests = generator.generate_for_class(cls, include_edge_cases)
        test_cases.extend(class_tests)

    # Add warnings
    if not test_cases:
        warnings.append("No testable functions or classes found")

    return GeneratedTest(
        module_name=module_name,
        imports=imports,
        test_cases=test_cases,
        warnings=warnings
    )

def generate_tests_with_ai(
    analysis: AnalysisResult,
    source_code: str,
    module_name: str = "module",
    include_edge_cases: bool = True,
    api_key: str | None = None
) -> GeneratedTest:
    """
    Generate tests with optional AI enhancement.
    
    Pipeline:
    1. Template generator creates basic tests (Layer 1+2)
    2. AI enhancer improves assertions (Layer 3)
    3. Fallback to template if AI fails
    
    Args:
        analysis: Result from analyze_code()
        source_code: Original source code
        module_name: Name for imports
        include_edge_cases: Whether to generate boundary tests
        api_key: OpenAI API key (optional, uses env var if not provided)
        
    Returns:
        GeneratedTest with complete test code
    """
    from .ai import create_enhancer

    # Step 1: Generate template tests (always runs)
    result = generate_tests(
        analysis=analysis,
        source_code=source_code,
        module_name=module_name,
        include_edge_cases=include_edge_cases
    )

    # Step 2: Try AI enhancement
    enhancer = create_enhancer(api_key=api_key)

    if not enhancer.is_available():
        result.warnings.append("AI enhancement skipped: No API key configured")
        return result

    enhancement = enhancer.enhance_tests(
        source_code=source_code,
        test_cases=result.test_cases
    )

    if enhancement.success:
        # Replace with enhanced tests
        result.test_cases = enhancement.enhanced_tests

        # Add AI suggestions as comments
        if enhancement.ai_suggestions:
            result.warnings.append(f"AI suggestions: {', '.join(enhancement.ai_suggestions)}")
    else:
        result.warnings.append(f"AI enhancement failed: {enhancement.error}. Using template tests.")

    return result
