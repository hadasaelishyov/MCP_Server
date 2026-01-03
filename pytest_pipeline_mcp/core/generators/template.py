"""
Template Generator - Main test generation engine.

Combines Layer 1 (basic templates) + Layer 2 (evidence-based enrichment).
"""

from ..analyzer.models import AnalysisResult, ClassInfo, FunctionInfo
from .base import GeneratedTest, GeneratedTestCase, TestGeneratorBase
from .extractors.boundary_values import generate_boundary_values, get_default_value
from .extractors.doctest_extractor import doctest_to_assertion, extract_doctests
from .extractors.type_assertions import generate_type_assertions
from .extractors.exception_detector import detect_exceptions, generate_exception_test, infer_trigger_overrides


class TemplateGenerator(TestGeneratorBase):
    """Generate pytest cases from analysis signals (doctests, hints, exceptions, boundaries)."""

    def __init__(self, source_code: str = ""):
        """Create generator (source_code is used for exception detection)."""
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

        # Layer 2: Evidence-based tests FIRST

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

        # Layer 1: Smoke test ONLY as fallback when no evidence found
        if not tests:
            return [self._generate_basic_test(func)]
        return tests

    def generate_for_class(
        self,
        cls: ClassInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate test cases for a class."""
        tests = []

        # Test class instantiation (always)
        tests.append(self._generate_class_init_test(cls))

        # Test each public method
        for method in cls.methods:
            if method.name.startswith('_') and method.name != '__init__':
                continue
            if method.name == '__init__':
                continue

            # Layer 2: Try evidence-based tests for method FIRST
            method_evidence = self._generate_method_evidence_tests(cls, method, include_edge_cases)

            if method_evidence:
                tests.extend(method_evidence)
            else:
                # Layer 1: Fallback to smoke test
                smoke = self._generate_method_smoke_test(cls, method)
                tests.append(smoke)

        return tests

    # =========================================================================
    # Layer 1: Basic Tests (Smoke Tests)
    # =========================================================================

    def _generate_basic_test(self, func: FunctionInfo) -> GeneratedTestCase:
        """Generate smoke test - ONLY verifies function runs without error."""
        body = []

        params = self._build_param_assignments(func)
        body.extend(params)

        call = self._build_function_call(func)
        body.append(f"result = {call}")

        # No fake assertion - just verify it runs
        body.append("# Smoke test: function executes without raising an exception")

        return GeneratedTestCase(
            name=f"test_{func.name}_smoke",
            description=f"Smoke test: {func.name} runs without error.",
            body=body,
            evidence_source="smoke"
        )

    def _generate_class_init_test(self, cls: ClassInfo) -> GeneratedTestCase:
        """Generate test for class instantiation."""
        body = []
        
        init_method = self._find_init_method(cls)
        
        # Check if __init__ has required parameters
        has_required_params = False
        if init_method:
            has_required_params = any(
                not p.has_default and self._get_clean_param_name(p.name) not in ('self', 'cls')
                for p in init_method.parameters
            )
        
        if init_method and has_required_params:
            # Generate parameters with proper defaults
            params = self._build_param_assignments(init_method, skip_self=True)
            body.extend(params)
            instance_call = self._build_class_instance(cls)
            body.append(f"instance = {instance_call}")
        else:
            # No required params - simple instantiation
            body.append(f"instance = {cls.name}()")
        
        body.append("assert instance is not None")
        body.append(f"assert isinstance(instance, {cls.name})")
        
        if init_method:
            for param in init_method.parameters:
                clean_name = self._get_clean_param_name(param.name)
                if clean_name not in ('self', 'cls', 'args', 'kwargs'):
                    # Check if attribute was likely set
                    body.append(f"# Verify instance was initialized properly")
                    break
        
        return GeneratedTestCase(
            name=f"test_{cls.name.lower()}_creation",
            description=f"Test {cls.name} can be instantiated and is of correct type.",
            body=body,
            evidence_source="template"
        )
        
    def _generate_method_smoke_test(
        self,
        cls: ClassInfo,
        method: FunctionInfo
    ) -> GeneratedTestCase:
        """Generate smoke test for a method (fallback when no evidence)."""
        body = []

        # Build instance with proper init params
        init_method = self._find_init_method(cls)
        if init_method:
            init_params = self._build_param_assignments(init_method, skip_self=True)
            body.extend(init_params)

        instance_call = self._build_class_instance(cls)
        body.append(f"instance = {instance_call}")

        # Build method call
        method_params = self._build_param_assignments(method, skip_self=True)
        body.extend(method_params)

        call = self._build_method_call(method)
        body.append(f"result = instance.{call}")

        # No fake assertion
        body.append("# Smoke test: method executes without raising an exception")

        return GeneratedTestCase(
            name=f"test_{cls.name.lower()}_{method.name}_smoke",
            description=f"Smoke test: {cls.name}.{method.name}() runs without error.",
            body=body,
            evidence_source="smoke"
        )

    def _generate_method_tests(
        self,
        cls: ClassInfo,
        method: FunctionInfo,
        include_edge_cases: bool
    ) -> list[GeneratedTestCase]:
        """Generate tests for a class method (DEPRECATED - use evidence-first approach)."""
        # Keep for backward compatibility, delegates to smoke test
        return [self._generate_method_smoke_test(cls, method)]

    # =========================================================================
    # Layer 2: Evidence-Based Tests
    # =========================================================================

    def _generate_method_evidence_tests(
        self,
        cls: ClassInfo,
        method: FunctionInfo,
        include_edge_cases: bool = True
    ) -> list[GeneratedTestCase]:
        """Generate evidence-based tests for a method. Returns empty if no evidence."""
        tests = []

        # From doctests
        if method.docstring:
            doctest_cases = self._generate_method_doctests(cls, method)
            tests.extend(doctest_cases)

        # From type hints
        if method.return_type:
            type_test = self._generate_method_type_test(cls, method)
            if type_test:
                tests.append(type_test)

        # From naming heuristics
        heuristic_test = self._generate_method_naming_test(cls, method)
        if heuristic_test:
            tests.append(heuristic_test)

        return tests

    def _generate_method_doctests(
        self,
        cls: ClassInfo,
        method: FunctionInfo
    ) -> list[GeneratedTestCase]:
        """Generate tests from method docstring examples."""
        if not method.docstring:
            return []

        tests = []
        examples = extract_doctests(method.docstring)

        for i, example in enumerate(examples):
            assertion = doctest_to_assertion(example, method.name)
            if assertion:
                body = []

                # Build instance
                init_method = self._find_init_method(cls)
                if init_method:
                    init_params = self._build_param_assignments(init_method, skip_self=True)
                    body.extend(init_params)

                instance_call = self._build_class_instance(cls)
                body.append(f"instance = {instance_call}")

                # Add assertion (may need adjustment for method calls)
                body.append(assertion)

                test_name = f"test_{cls.name.lower()}_{method.name}_doctest_{i + 1}"
                tests.append(GeneratedTestCase(
                    name=test_name,
                    description=f"Test {cls.name}.{method.name} with documented example.",
                    body=body,
                    evidence_source="doctest"
                ))

        return tests

    def _generate_method_type_test(
        self,
        cls: ClassInfo,
        method: FunctionInfo
    ) -> GeneratedTestCase | None:
        """Generate type test for a method."""
        assertions = generate_type_assertions(method.return_type)

        if not assertions:
            return None

        body = []

        # Build instance
        init_method = self._find_init_method(cls)
        if init_method:
            init_params = self._build_param_assignments(init_method, skip_self=True)
            body.extend(init_params)

        instance_call = self._build_class_instance(cls)
        body.append(f"instance = {instance_call}")

        # Build method call
        method_params = self._build_param_assignments(method, skip_self=True)
        body.extend(method_params)

        call = self._build_method_call(method)
        body.append(f"result = instance.{call}")

        # Add type assertions
        body.extend(assertions)

        return GeneratedTestCase(
            name=f"test_{cls.name.lower()}_{method.name}_return_type",
            description=f"Test {cls.name}.{method.name}() returns correct type.",
            body=body,
            evidence_source="type_hint"
        )

    def _generate_method_naming_test(
        self,
        cls: ClassInfo,
        method: FunctionInfo
    ) -> GeneratedTestCase | None:
        """Generate test based on method naming convention."""
        name = method.name.lower()

        if not (name.startswith('is_') or name.startswith('has_')):
            return None

        body = []

        # Build instance
        init_method = self._find_init_method(cls)
        if init_method:
            init_params = self._build_param_assignments(init_method, skip_self=True)
            body.extend(init_params)

        instance_call = self._build_class_instance(cls)
        body.append(f"instance = {instance_call}")

        # Build method call
        method_params = self._build_param_assignments(method, skip_self=True)
        body.extend(method_params)

        call = self._build_method_call(method)
        body.append(f"result = instance.{call}")
        body.append("assert isinstance(result, bool), f'Expected bool, got {type(result)}'")

        return GeneratedTestCase(
            name=f"test_{cls.name.lower()}_{method.name}_returns_boolean",
            description=f"Test {cls.name}.{method.name}() returns boolean (naming convention).",
            body=body,
            evidence_source="naming_heuristic"
        )

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
            typed_params = []
            for p in func.parameters:
                name = self._get_clean_param_name(p.name)
                if name in ("self", "cls"):
                    continue
                typed_params.append((name, p.type_hint))

            overrides = infer_trigger_overrides(getattr(exc, "condition_ast", None), typed_params)

            values = []
            for name, hint in typed_params:
                if name in overrides:
                    values.append(overrides[name])
                else:
                    values.append(get_default_value(hint, name))

            param_values = ", ".join(values)

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
            if p.type_hint and self._get_clean_param_name(p.name) not in ('self', 'cls')
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
                clean_name = self._get_clean_param_name(p.name)
                if clean_name in ('self', 'cls'):
                    continue

                if p.name == param.name:
                    body.append(f"{clean_name} = {boundary.value}")
                else:
                    body.append(f"{clean_name} = {get_default_value(p.type_hint)}")

            call = self._build_function_call(func)
            body.append(f"result = {call}")
            body.append("# Verify function handles boundary value")

            if func.return_type:
                assertions = generate_type_assertions(func.return_type)
                body.extend(assertions)
            else:
                body.append("# Boundary test: function handles edge case without error")

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

    def _get_clean_param_name(self, name: str) -> str:
        """Remove * or ** prefix from parameter name."""
        if name.startswith('**'):
            return name[2:]
        if name.startswith('*'):
            return name[1:]
        return name

    def _find_init_method(self, cls: ClassInfo) -> FunctionInfo | None:
        """Find __init__ method in a class."""
        for method in cls.methods:
            if method.name == '__init__':
                return method
        return None

    def _build_class_instance(self, cls: ClassInfo) -> str:
        """Build class instantiation string with proper init params."""
        init_method = self._find_init_method(cls)

        if not init_method:
            return f"{cls.name}()"

        param_parts = []
        for p in init_method.parameters:
            clean_name = self._get_clean_param_name(p.name)
            if clean_name in ('self', 'cls'):
                continue

            # Handle *args and **kwargs in call
            if p.name.startswith('**'):
                param_parts.append(f"**{clean_name}")
            elif p.name.startswith('*'):
                param_parts.append(f"*{clean_name}")
            else:
                param_parts.append(clean_name)

        if param_parts:
            return f"{cls.name}({', '.join(param_parts)})"
        return f"{cls.name}()"

    def _build_param_assignments(
        self,
        func: FunctionInfo,
        skip_self: bool = False
    ) -> list[str]:
        """Build parameter assignment lines."""
        lines = []

        for param in func.parameters:
            clean_name = self._get_clean_param_name(param.name)

            if skip_self and clean_name in ('self', 'cls'):
                continue

            # Handle *args and **kwargs
            if param.name.startswith('**'):
                # **kwargs → kwargs = {}
                lines.append(f"{clean_name} = {{}}")
            elif param.name.startswith('*'):
                # *args → args = []
                lines.append(f"{clean_name} = []")
            elif param.has_default and param.default_value:
                lines.append(f"{clean_name} = {param.default_value}")
            else:
                value = get_default_value(param.type_hint, clean_name)
                lines.append(f"{clean_name} = {value}")

        return lines

    def _build_function_call(self, func: FunctionInfo) -> str:
        """Build function call string."""
        parts = []

        for p in func.parameters:
            clean_name = self._get_clean_param_name(p.name)
            if clean_name in ('self', 'cls'):
                continue

            # Preserve * and ** in the call
            if p.name.startswith('**'):
                parts.append(f"**{clean_name}")
            elif p.name.startswith('*'):
                parts.append(f"*{clean_name}")
            else:
                parts.append(clean_name)

        if parts:
            return f"{func.name}({', '.join(parts)})"
        return f"{func.name}()"

    def _build_method_call(self, method: FunctionInfo) -> str:
        """Build method call string (without instance prefix)."""
        parts = []

        for p in method.parameters:
            clean_name = self._get_clean_param_name(p.name)
            if clean_name in ('self', 'cls'):
                continue

            # Preserve * and ** in the call
            if p.name.startswith('**'):
                parts.append(f"**{clean_name}")
            elif p.name.startswith('*'):
                parts.append(f"*{clean_name}")
            else:
                parts.append(clean_name)

        if parts:
            return f"{method.name}({', '.join(parts)})"
        return f"{method.name}()"

    def _build_param_values(self, func: FunctionInfo) -> str:
        """Build comma-separated param values for function call."""
        values = []
        for param in func.parameters:
            clean_name = self._get_clean_param_name(param.name)
            if clean_name in ('self', 'cls'):
                continue
            values.append(get_default_value(param.type_hint, clean_name))
        return ", ".join(values)


def generate_tests(
    analysis: AnalysisResult,
    source_code: str,
    module_name: str = "module",
    include_edge_cases: bool = True
) -> GeneratedTest:
    """Generate a complete GeneratedTest from an AnalysisResult (template-based)."""
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
    include_edge_cases: bool = True
    ) -> GeneratedTest:
    """Generate tests and optionally enhance them with AI (falls back to template on failure)."""

    from .ai import create_enhancer

    # Step 1: Generate template tests (always runs)
    result = generate_tests(
        analysis=analysis,
        source_code=source_code,
        module_name=module_name,
        include_edge_cases=include_edge_cases
    )

    # Step 2: Try AI enhancement
    enhancer = create_enhancer()

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