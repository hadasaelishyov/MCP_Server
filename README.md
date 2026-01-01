# Pytest Pipeline MCP Server

A Model Context Protocol (MCP) server providing a complete pytest pipeline: analyze code, generate tests, run with coverage, and auto-fix failures.


---

## Overview

Given a Python file or code string, the server can:

- **Analyze** code structure using AST parsing (functions, classes, methods), validate syntax, and report quality metrics
- **Generate** pytest tests using evidence from doctests, type hints, exceptions, and boundary values
- **Run** generated tests in an isolated environment with coverage reporting
- **Fix** failing code automatically using AI-assisted bug detection (optional, requires OpenAI API key)
- **Integrate** with GitHub to analyze repositories and create pull requests

---

## End-to-End Pipeline

A core design principle of this server is **tool composability**. Each tool's output is structured to serve as input for the next, enabling seamless chained workflows:

```
┌──────────────┐     ┌─────────────────┐     ┌───────────┐     ┌──────────┐
│ analyze_code │ ──▶ │ generate_tests  │ ──▶ │ run_tests │ ──▶ │ fix_code │
└──────────────┘     └─────────────────┘     └───────────┘     └──────────┘
       │                     │                     │                 │
       ▼                     ▼                     ▼                 ▼
   Code structure       Test code            Pass/fail +        Fixed code
   + warnings           ready to run         coverage           + verification
```

### Local Workflow

```python
# 1. Analyze the code
analyze_code(file_path="src/calculator.py")
    → Returns: functions, classes, complexity, type coverage, warnings

# 2. Generate tests (uses analysis internally)
generate_tests(file_path="src/calculator.py", include_edge_cases=True)
    → Returns: pytest test code with doctest, type, exception, and boundary tests

# 3. Run the generated tests
run_tests(source_code="...", test_code="<generated tests>")
    → Returns: pass/fail counts, coverage percentage, failure details

# 4. If tests fail, fix the code
fix_code(source_code="...", test_code="...", verify=True)
    → Returns: fixed code, bugs found, verification result
```

### GitHub Workflow

```python
# 1. Analyze a repository
analyze_repository(repo_url="https://github.com/user/repo")
    → Returns: list of files needing tests, with complexity and coverage metrics

# 2. Get a specific file
get_repo_file(repo_url="...", file_path="src/module.py")
    → Returns: file content

# 3. Generate tests for that file
generate_tests(code="<file content>")
    → Returns: pytest test code

# 4. Create a PR with the tests
create_test_pr(repo_url="...", test_code="...", target_file="src/module.py")
    → Returns: PR URL and number

# 5. After CI runs, post results
comment_test_results(repo_url="...", pr_number=42, test_results="...")
    → Returns: comment URL
```

This composability means an MCP-compatible agent can orchestrate the entire test-generation-and-fix cycle without manual intervention.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **AST-based analysis** | Parses Python code using Abstract Syntax Tree for accurate structure extraction |
| **Evidence-first generation** | Tests derived from doctests, type hints, raise statements, and boundary values |
| **Layered pipeline** | Template tests → evidence enrichment → optional AI enhancement |
| **Isolated execution** | Tests run in temp directory with 30s timeout and coverage |
| **Automatic fixing** | AI analyzes failures, generates minimal fixes, verifies by re-running |
| **GitHub integration** | Clone repos, create PRs, post comments—all via tool calls |

---

## Installation

### Requirements

- Python 3.10+
- Recommended: [uv](https://github.com/astral-sh/uv)

### Quick Start

```bash
git clone https://github.com/hadasaelishyov/pytest-pipeline-mcp.git
cd pytest-pipeline-mcp
uv sync
uv run pytest-pipeline-mcp
```

### Optional Environment Variables

```bash
export OPENAI_API_KEY="..."   # For AI-enhanced generation and fixing
export GITHUB_TOKEN="..."      # For GitHub integration
```

---

## Tool Reference

### Core Tools

| Tool | Purpose | Required Inputs |
|------|---------|-----------------|
| `analyze_code` | Parse code via AST, validate syntax, report metrics | `file_path` or `code` |
| `generate_tests` | Generate pytest tests with evidence-based enrichment | `file_path` or `code` |
| `run_tests` | Execute tests in isolated environment with coverage | `source_code`, `test_code` |
| `fix_code` | AI-assisted bug fixing with verification | `source_code`, `test_code` |

### GitHub Tools

| Tool | Purpose | Required Inputs |
|------|---------|-----------------|
| `analyze_repository` | Clone and analyze repo for test coverage gaps | `repo_url` |
| `get_repo_file` | Retrieve file content from a repository | `repo_url`, `file_path` |
| `create_test_pr` | Create PR with generated tests | `repo_url`, `test_code`, `target_file` |
| `comment_test_results` | Post test results on a PR | `repo_url`, `pr_number`, `test_results` |

---

## Architecture

```
pytest_pipeline_mcp/
├── server.py              # MCP entry point (thin routing layer)
├── handlers/              # Tool handlers (MCP ↔ services)
│   ├── core/              # analyze, generate, run, fix
│   └── github/            # repo analysis, PR creation, comments
├── services/              # Business logic (testable without MCP)
│   ├── base.py            # ServiceResult pattern, error codes
│   ├── analysis.py        # AnalysisService
│   ├── generation.py      # GenerationService
│   ├── execution.py       # ExecutionService
│   └── github.py          # GitHubService
└── core/                  # Pure logic (no framework dependencies)
    ├── analyzer/          # AST parsing, syntax validation, type checking
    ├── generators/        # Template + AI test generation
    ├── runner/            # pytest execution, coverage
    └── fixer/             # AI-powered bug fixing
```

**Design principles:**
- **Separation of concerns**: Server → Handlers → Services → Core
- **ServiceResult pattern**: All operations return success/failure with structured errors
- **Dependency injection**: Services accept dependencies via `__init__` for testability
- **Framework independence**: Core modules have no MCP or external framework dependencies

---

## Test Generation Pipeline

The generator uses a three-layer approach:

1. **Layer 1 (Template)**: Basic smoke tests for all public functions and methods
2. **Layer 2 (Evidence)**: Enrichment from concrete signals in the code:
   - Doctest examples → exact assertions
   - Type annotations → type checks and boundary values
   - Raise statements → `pytest.raises` tests
   - Naming conventions → boolean assertions for `is_*`/`has_*`
3. **Layer 3 (AI, optional)**: OpenAI-enhanced assertions with computed expected values

---

## Limitations

- Tests run in subprocess with 30-second timeout
- `fix_code` and AI enhancement require OpenAI API key
- GitHub operations subject to rate limits
- Class tests assume no-argument constructors
- Complex import patterns may need manual adjustment

---

## Security Notes

This server executes Python code. Do not run untrusted code without sandboxing. Store API keys securely and use minimal GitHub token permissions.

---

## Contributing

```bash
git clone https://github.com/hadasaelishyov/pytest-pipeline-mcp.git
cd pytest-pipeline-mcp
uv sync
uv run pytest                   
uv run ruff check pytest_pipeline_mcp/
```

---