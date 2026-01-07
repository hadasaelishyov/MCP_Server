"""Execute pytest in an isolated temp workspace and parse results/coverage."""


import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final
import asyncio

from .models import CoverageResult, RunResult, TestResult

# Standard library modules to skip when detecting imports
STDLIB_MODULES: Final[frozenset[str]] = frozenset({
    'pytest', 'unittest', 'typing', 'collections',
    'os', 'sys', 'json', 're', 'ast', 'pathlib'
})

class PytestRunner:
    """Run pytest for provided source+tests and return structured results."""

    def __init__(self, source_code: str, test_code: str):
        """Store inputs and infer the tested module name from test imports."""

        self.source_code = source_code
        self.test_code = test_code
        self.module_name = self._detect_module_name(test_code)

    def _detect_module_name(self, test_code: str) -> str:
        """Infer module name from 'from X import ...' lines in test code."""
        
        for line in test_code.split('\n'):
            line = line.strip()

            # Match: from module_name import ...
            if line.startswith('from ') and ' import ' in line:
                match = re.match(r'from\s+(\w+)\s+import', line)
                if match:
                    module = match.group(1)
                    # Skip standard library imports
                    if module not in STDLIB_MODULES:
                        return module

        return "module"  # default fallback

    async def run(self) -> RunResult:
        """Write files to a temp dir, run pytest+coverage, and return a RunResult."""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Write source file with detected module name
                source_file = temp_path / f"{self.module_name}.py"
                source_file.write_text(self.source_code, encoding='utf-8')

                # Write test file (no modifications needed!)
                test_file = temp_path / f"test_{self.module_name}.py"
                test_file.write_text(self.test_code, encoding='utf-8')

                # Run pytest with coverage
                result = await self._run_pytest(temp_path, source_file, test_file)

                return result

        except Exception as e:
            return RunResult(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                test_results=[],
                coverage=None,
                success=False,
                error_message=f"Runner error: {str(e)}"
            )

    async def _run_pytest(
        self,
        temp_path: Path,
        source_file: Path,
        test_file: Path
    ) -> RunResult:
        """Execute pytest subprocess and parse test+coverage results."""

        coverage_json = temp_path / "coverage.json"
        python_exe = sys.executable

        cmd = [
            python_exe, "-m", "pytest",
            str(test_file),
            f"--cov={self.module_name}",
            f"--cov-report=json:{coverage_json}",
            "--tb=short",
            "-v",
            "--no-header",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(temp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                env={**os.environ, "PYTHONPATH": str(temp_path)}
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            stdout = stdout_bytes.decode('utf-8')
            stderr = stderr_bytes.decode('utf-8')
            returncode = process.returncode
        except asyncio.TimeoutError:
            return RunResult(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                test_results=[],
                coverage=None,
                success=False,
                error_message="Test execution timed out (30s limit)"
            )
        except FileNotFoundError:
            return RunResult(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                test_results=[],
                coverage=None,
                success=False,
                error_message="pytest not found. Install with: pip install pytest pytest-cov"
            )
        except Exception as e:
            return RunResult(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                test_results=[],
                coverage=None,
                success=False,
                error_message=f"Execution error: {str(e)}"
            )

        # Parse test results
        test_results = self._parse_pytest_output(stdout, stderr)

        # Parse coverage
        coverage = self._parse_coverage(coverage_json)

        # Count results
        passed = sum(1 for t in test_results if t.passed)
        failed = sum(1 for t in test_results if not t.passed)
        total = len(test_results)

        # Check for errors
        errors = 0
        error_message = None

        if returncode != 0 and total == 0:
            errors = 1
            error_message = self._extract_error(stdout, stderr)

        return RunResult(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            test_results=test_results,
            coverage=coverage,
            success=(failed == 0 and errors == 0),
            error_message=error_message
        )

    def _parse_pytest_output(self, stdout: str, stderr: str) -> list[TestResult]:
        """Parse pytest output into TestResult entries."""
        
        results = []
        combined_output = stdout + "\n" + stderr

        for line in combined_output.split('\n'):
            line = line.strip()

            # Look for test result lines like:
            # test_module.py::test_add_basic PASSED
            # test_module.py::test_divide_raises FAILED
            if '::test_' in line and (' PASSED' in line or ' FAILED' in line or ' ERROR' in line):
                # Extract test name
                if '::' in line:
                    parts = line.split('::')
                    if len(parts) >= 2:
                        test_part = parts[1].split()[0]  # Get test name before PASSED/FAILED
                        test_name = test_part.strip()

                        passed = ' PASSED' in line
                        error_msg = None

                        if not passed:
                            error_msg = self._extract_test_error(test_name, combined_output)

                        results.append(TestResult(
                            name=test_name,
                            passed=passed,
                            error_message=error_msg
                        ))

        return results

    def _extract_test_error(self, test_name: str, output: str) -> str:
        """Extract error message for a failed test."""
        lines = output.split('\n')

        # Look for assertion errors or exceptions
        capturing = False
        error_lines = []

        for line in lines:
            if test_name in line and ('FAILED' in line or 'ERROR' in line):
                capturing = True
                continue

            if capturing:
                if line.strip().startswith('_') or line.strip().startswith('='):
                    if error_lines:
                        break
                    continue

                if 'AssertionError' in line or 'Error' in line or 'Exception' in line:
                    error_lines.append(line.strip())
                elif line.strip().startswith('E '):
                    error_lines.append(line.strip()[2:])  # Remove 'E ' prefix
                elif line.strip().startswith('>'):
                    error_lines.append(line.strip())

        if error_lines:
            return ' | '.join(error_lines[:3])  # Limit to 3 lines

        return "Test failed (see full output for details)"

    def _extract_error(self, stdout: str, stderr: str) -> str:
        """Extract general error message from pytest output."""
        combined = stdout + "\n" + stderr

        # Look for common error patterns
        if "ModuleNotFoundError" in combined:
            for line in combined.split('\n'):
                if "ModuleNotFoundError" in line:
                    return line.strip()

        if "ImportError" in combined:
            for line in combined.split('\n'):
                if "ImportError" in line:
                    return line.strip()

        if "SyntaxError" in combined:
            for line in combined.split('\n'):
                if "SyntaxError" in line:
                    return line.strip()

        if "no tests ran" in combined.lower():
            return "No tests were found or executed"

        # Return last non-empty line as fallback
        for line in reversed(combined.split('\n')):
            if line.strip() and not line.startswith('='):
                return line.strip()[:200]  # Limit length

        return "Unknown error occurred"

    def _parse_coverage(self, coverage_file: Path) -> CoverageResult | None:
        """Parse coverage JSON report into a CoverageResult (or None)."""

        if not coverage_file.exists():
            return None

        try:
            content = coverage_file.read_text(encoding='utf-8')
            if not content.strip():
                return None

            data = json.loads(content)


            # Get totals
            totals = data.get('totals', {})

            percentage = totals.get('percent_covered', 0.0)
            covered_lines = totals.get('covered_lines', 0)
            total_lines = totals.get('num_statements', 0)

            # Get missing lines from files
            missing_lines = []
            files = data.get('files', {})

            for file_data in files.values():
                missing = file_data.get('missing_lines', [])
                missing_lines.extend(missing)

            return CoverageResult(
                percentage=percentage,
                covered_lines=covered_lines,
                total_lines=total_lines,
                missing_lines=sorted(missing_lines)
            )

        except (json.JSONDecodeError, KeyError):
            return None


async def run_tests(source_code: str, test_code: str) -> RunResult:
    """Convenience wrapper that runs tests via PytestRunner."""
    runner = PytestRunner(source_code, test_code)
    return await runner.run()
