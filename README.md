# 🧪 Pytest Generator MCP Server

> **AI-powered test generation for Python code** — Analyze, Generate, Execute

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-45%2B%20passing-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ What It Does

A complete test automation pipeline as an MCP (Model Context Protocol) server. Works with Claude Desktop, MCP Inspector, and any MCP-compatible client.

```
┌──────────────────────────────────────────────────────────────┐
│                    COMPLETE PIPELINE                          │
│                                                               │
│   📄 Your Code                                                │
│        ↓                                                      │
│   🔍 analyze_code    → Structure, complexity, warnings        │
│        ↓                                                      │
│   🧪 generate_tests  → Template + AI enhanced tests           │
│        ↓                                                      │
│   ▶️  run_tests      → Pass/fail results + coverage           │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Features

### 🔍 Code Analysis (`analyze_code`)
- AST-based parsing of Python code
- Extracts functions, classes, methods, parameters
- Calculates cyclomatic complexity
- Reports type hint coverage
- Warns about missing docstrings and high complexity

### 🧪 Test Generation (`generate_tests`)

**Layer 1 — Template Tests**
- Basic smoke tests for every function
- Class instantiation tests
- Method invocation tests

**Layer 2 — Evidence-Based Enrichment**
- 📝 **Doctest Extraction** — Converts docstring examples to assertions
- 🏷️ **Type Assertions** — Generates `isinstance` checks from type hints
- ⚠️ **Exception Detection** — Creates `pytest.raises` tests from AST
- 📊 **Boundary Values** — Tests edge cases (zero, empty, negative)
- 🔤 **Naming Heuristics** — `is_*` → boolean, `get_*` → returns value

**Layer 3 — AI Enhancement** (Optional)
- 🤖 Uses OpenAI to enhance weak assertions
- Replaces `assert result is not None` with `assert result == 5`
- Fixes exception trigger conditions
- Adds meaningful edge case tests
- Falls back to templates if AI unavailable

### ▶️ Test Execution (`run_tests`)
- Runs tests in isolated temporary environment
- Reports pass/fail with detailed error messages
- Measures actual code coverage via `pytest-cov`
- Auto-detects module name from imports

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-pytest-generator.git
cd mcp-pytest-generator

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### Configure Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "pytest-generator": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:\\path\\to\\project",
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

---

## 🎯 Usage

### With MCP Inspector

```bash
npx @modelcontextprotocol/inspector .venv\Scripts\python.exe -m src.server
```

### With Claude Desktop

Once configured, Claude can use the tools directly:

**"Analyze this code"** → Uses `analyze_code`

**"Generate tests for this code"** → Uses `generate_tests`

**"Generate tests with AI enhancement"** → Uses `generate_tests` with `use_ai=true`

**"Run these tests"** → Uses `run_tests`

---

## 📖 Examples

### Example 1: Simple Function

**Input Code:**
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

**Generated Tests (AI-enhanced):**
```python
def test_calculate_discount_basic():
    assert calculate_discount(100.0, 20.0) == 80.0

def test_calculate_discount_doctest_1():
    assert calculate_discount(100.0, 10.0) == 90.0

def test_calculate_discount_raises_valueerror():
    with pytest.raises(ValueError):
        calculate_discount(100.0, -5.0)
    with pytest.raises(ValueError):
        calculate_discount(100.0, 150.0)

def test_calculate_discount_zero_discount():
    assert calculate_discount(100.0, 0.0) == 100.0

def test_calculate_discount_full_discount():
    assert calculate_discount(100.0, 100.0) == 0.0
```

### Example 2: Run Tests Output

```
🧪 TEST EXECUTION RESULTS
==================================================

✅ All tests passed!

📊 Summary:
  • Total:  5
  • Passed: 5
  • Failed: 0

📈 Code Coverage:
  • Coverage: 100.0%
  • Lines covered: 6/6

✅ Passed tests:
  • test_calculate_discount_basic
  • test_calculate_discount_doctest_1
  • test_calculate_discount_raises_valueerror
  • test_calculate_discount_zero_discount
  • test_calculate_discount_full_discount
```

---

## 🏗️ Architecture

```
src/
├── server.py                 # MCP server entry point
├── core/                     # Code analysis engine
│   ├── analyzer.py           # Main analyzer
│   ├── parser.py             # AST parsing
│   └── models.py             # Data models
├── generators/               # Test generation
│   ├── template_generator.py # Layer 1+2: Templates
│   ├── ai_enhancer.py        # Layer 3: AI enhancement
│   ├── base.py               # Base classes
│   └── evidence/             # Evidence extractors
│       ├── doctest_extractor.py
│       ├── type_assertions.py
│       ├── exception_detector.py
│       └── boundary_values.py
├── runner/                   # Test execution
│   ├── executor.py           # Pytest runner
│   └── models.py             # Result models
└── validation/               # Code validation
```

### Design Decisions

**Why Hybrid AI + Templates?**

| Templates | AI |
|-----------|-----|
| ✅ 100% accurate (from code) | ✅ Understands logic |
| ✅ Always available | ❌ Requires API key |
| ✅ Free | ❌ Costs money |
| ❌ Can't compute expected values | ✅ Generates real assertions |

**Solution:** Templates provide reliable foundation, AI enhances when available. If AI fails, you still get useful tests.

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_generators.py -v
```

**Test Coverage:**
- Core modules: ~45+ tests
- Generators: Template + AI enhancer tests
- Runner: Execution and coverage tests
- Server: Integration tests

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI enhancement | Optional |

### Tool Parameters

**`generate_tests`**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | string | — | Python code to test |
| `file_path` | string | — | Alternative: path to file |
| `use_ai` | boolean | `false` | Enable AI enhancement |
| `include_edge_cases` | boolean | `true` | Generate boundary tests |

**`run_tests`**
| Parameter | Type | Description |
|-----------|------|-------------|
| `source_code` | string | Python source code |
| `test_code` | string | Pytest test code |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [OpenAI](https://openai.com/) for AI enhancement capabilities
- [pytest](https://pytest.org/) for the testing framework
