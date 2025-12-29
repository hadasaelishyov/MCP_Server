# 🧪 Pytest Generator MCP Server

> **Evidence-first test generation for Python** — Analyze → Generate → Run → Fix  
> Built as an **MCP (Model Context Protocol) server** for coding agents (Claude Desktop / MCP Inspector and other MCP clients).

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-300%2B-green.svg)](#-testing)
[![Coverage](https://img.shields.io/badge/coverage-~77%25-yellowgreen.svg)](#-testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

---

## ✨ What It Does

Pytest Generator MCP is a complete test automation pipeline exposed as MCP tools. It analyzes Python code, generates runnable pytest test suites, executes them in an isolated environment, and (optionally) proposes fixes based on failures.

### Core workflow

```
┌──────────────────────────────────────────────────────────────┐
│                        CORE TOOLS                             │
│                                                              │
│  📄 Source Code                                               │
│     ↓                                                        │
│  🔍 analyze_code     → AST structure, complexity, warnings    │
│     ↓                                                        │
│  🧪 generate_tests   → Templates + evidence-based assertions  │
│     ↓                                                        │
│  ▶️  run_tests       → Pass/fail + coverage report            │
│     ↓ (optional)                                            │
│  🛠️  fix_code        → AI-assisted fixes + verification       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Optional GitHub workflow (plugin)

When enabled with a `GITHUB_TOKEN`, the server can integrate with a GitHub development workflow: analyze a repository, generate tests for selected files, and optionally create pull requests and comment results.

---

## 🚀 Features

### 🔍 Code Analysis (`analyze_code`)
- AST-based parsing of Python code
- Extracts functions, classes, methods, and parameters (including `positional_only`, `keyword_only`, `*args`, `**kwargs`)
- Calculates cyclomatic complexity and basic statistics
- Reports type-hint coverage and warns about missing hints / high complexity
- Designed to be deterministic and safe (static analysis only)

### 🧪 Test Generation (`generate_tests`)

**Layer 1 — Template Tests**
- Generates runnable smoke tests for each function
- Generates class instantiation tests
- Generates method invocation tests for class methods

**Layer 2 — Evidence-Based Enrichment**
- 📝 **Doctest Extraction** — converts docstring examples to real `assert` statements
- 🏷️ **Type Assertions** — safe `isinstance` checks derived from type annotations (including Optionals/Unions)
- ⚠️ **Exception Detection** — generates `pytest.raises(...)` tests inferred from AST `raise` statements
- 📊 **Boundary Values** — edge cases such as `0/-1/""/[]/{}` and other type-shaped boundaries
- 🔤 **Naming Heuristics** — adds hints for `is_*` and `get_*` style functions

**Layer 3 — AI Enhancement (Optional)**
- Strengthens weak assertions when static evidence is insufficient
- Improves exception trigger conditions and adds additional edge cases
- Cleanly falls back to template/evidence tests if AI is unavailable

> **Design rule:** *Never guess expected values without evidence.*  
> Wrong tests are worse than weak tests — templates + evidence are the guardrails, AI is an optional booster.

### ▶️ Test Execution (`run_tests`)
- Runs tests inside an isolated temporary directory
- Returns a structured summary (passed/failed totals + failure details)
- Supports coverage reporting using `pytest-cov`
- Auto-detects module name and imports to keep generated tests runnable

### 🛠️ Code Fixing (`fix_code`) (Optional)
- Parses pytest output and identifies failing areas
- Uses AI (when enabled) to propose patches to the source code
- Can verify fixes by re-running tests and returning a verification summary

---

## 🔗 GitHub Tools (Optional Plugin)

GitHub tools are available only when `GITHUB_TOKEN` is provided (recommended to keep them optional and disabled by default).

### 🔍 `analyze_repository`
- Clones a repository to a temporary folder
- Analyzes Python files (optionally with path filters)
- Identifies files likely needing tests and returns a structured report

### 🧷 `create_test_pr`
- Creates a new branch
- Writes/updates generated tests under `tests/`
- Opens a pull request with a clean description

### 💬 `comment_test_results`
- Adds test results and coverage summary as a PR comment

> Recommended usage: for trusted repos and demo workflows. Network/API failures should be handled gracefully.

---

## 📦 Installation

### Requirements
- Python 3.10+
- `uv` recommended (or `pip`)

### Setup

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# Install dependencies
uv sync

# Run tests
uv run pytest -q
```

If you prefer pip:

```bash
pip install -e .
pytest -q
```

---

## 🧠 Run as an MCP Server

### Using MCP Inspector

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python.exe -m src.server
```

### Using Claude Desktop (Windows example)

Edit:
`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pytest-generator": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:\\path\\to\\project",
      "env": {
        "OPENAI_API_KEY": "sk-optional",
        "GITHUB_TOKEN": "ghp-optional"
      }
    }
  }
}
```

Notes:
- `OPENAI_API_KEY` is optional (only needed for AI enhancement and AI fixing).
- `GITHUB_TOKEN` is optional (only needed for GitHub integration tools).

---

## 🎯 Tool Reference

### Core Tools

| Tool | Purpose |
|------|---------|
| `analyze_code` | Parse and extract structure + warnings |
| `generate_tests` | Generate pytest suite (templates + evidence + optional AI) |
| `run_tests` | Execute tests and report pass/fail + coverage |
| `fix_code` | Optional AI fixer for failures, with verification |

### GitHub Tools (Optional)

| Tool | Purpose |
|------|---------|
| `analyze_repository` | Clone and analyze repo, find files needing tests |
| `create_test_pr` | Create PR that adds/updates tests |
| `comment_test_results` | Comment results and coverage on PR |

---

## 📖 Examples

### Example: Input Code

```python
def calculate_discount(price: float, percentage: float) -> float:
    """Calculate discounted price.

    >>> calculate_discount(100.0, 10.0)
    90.0
    """
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")
    return price * (1 - percentage / 100)
```

### Example: Generated Tests (evidence-based)

```python
import pytest

from your_module import calculate_discount

def test_calculate_discount_doctest_1():
    assert calculate_discount(100.0, 10.0) == 90.0

def test_calculate_discount_raises_valueerror():
    with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
        calculate_discount(100.0, -1.0)
    with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
        calculate_discount(100.0, 101.0)

def test_calculate_discount_boundary_values():
    assert calculate_discount(100.0, 0.0) == 100.0
    assert calculate_discount(100.0, 100.0) == 0.0
```

### Example: Test Execution Output (summarized)

```
🧪 TEST EXECUTION RESULTS
==================================================

✅ All tests passed!

📊 Summary:
  • Total:  3
  • Passed: 3
  • Failed: 0

📈 Code Coverage:
  • Coverage: 100.0%
```

---

## 🏗️ Architecture

The server is intentionally thin: it only handles MCP protocol wiring.  
Business logic lives in services and tool modules for testability and separation of concerns.

```
src/
├── server.py                      # MCP server entry point
├── constants.py
├── services/                      # Orchestration + shared patterns
│   ├── base.py                    # ServiceResult, ErrorCode
│   ├── code_loader.py
│   ├── analysis.py
│   ├── generation.py
│   ├── execution.py
│   ├── fixing.py
│   └── github.py
└── tools/
    ├── core/                      # Core MCP tools
    │   ├── analyze_code.py
    │   ├── generate_tests.py
    │   ├── run_tests.py
    │   ├── fix_code.py
    │   ├── analyzer/              # AST parsing + models
    │   ├── generators/            # template + evidence + ai enhancer
    │   ├── runner/                # pytest runner + coverage models
    │   └── fixer/                 # AI fixer + failure parsing
    └── github/                    # GitHub integration tools (optional)
        ├── analyze_repository.py
        ├── create_test_pr.py
        └── comment_test_results.py
```

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run a specific file
uv run pytest tests/test_tool_handlers.py -v
```

The test suite includes:
- Unit tests for analyzers, evidence extractors, generators, runner, and services
- Integration tests for full flows (analyze → generate → run)
- GitHub integration tests with mocked API behavior

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Enables AI enhancement and AI fixing | Optional |
| `GITHUB_TOKEN` | Enables GitHub integration tools | Optional |

### Key Tool Parameters (high level)

`generate_tests`
- `code` (string) OR `file_path` (string)
- `use_ai` (bool, default: false)
- `include_edge_cases` (bool, default: true)

`run_tests`
- `source_code` (string)
- `test_code` (string)

`fix_code`
- `source_code` (string)
- `test_code` (string)
- `verify` (bool, default: true)

---

## 🔒 Security Notes

This project can execute Python code via `pytest` when using `run_tests`.

- ✅ Intended for trusted code (your own local projects / controlled repos)
- ⚠️ Do not run untrusted code without sandboxing and stronger resource limits
- Keep `OPENAI_API_KEY` and `GITHUB_TOKEN` in env vars and never commit them

---

## 🗺️ Roadmap (Optional)

- `pipeline` tool: orchestrate analyze → generate → run → fix → rerun in one call (with step-by-step report)
- Mutation testing report (“mutation survivors” + actionable suggestions)
- Stronger sandboxing (timeouts, resource limits, container execution)

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgments

- Model Context Protocol (MCP)
- pytest / pytest-cov
- OpenAI (optional AI enhancement/fixing)
