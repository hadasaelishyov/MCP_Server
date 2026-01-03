# Pytest Pipeline MCP Server

A Model Context Protocol (MCP) server providing a complete pytest pipeline: analyze code, generate tests, run with coverage, and auto-fix failures.

---

## Overview

Given a Python file or code string, the server can:

- **Analyze** code structure using AST parsing (functions, classes, methods), validate syntax, and report quality metrics
- **Generate** pytest tests using an **evidence-first** approach (doctests, type hints, exceptions, boundary values), with optional AI refinement
- **Run** generated tests in an isolated environment with coverage reporting
- **Fix** failing code automatically using AI-assisted bug detection (optional, requires OpenAI API key)
- **Integrate** with GitHub to analyze repositories and create pull requests
- **Quality**: Includes 300+ internal pytest tests (services/core/handlers) to keep the pipeline reliable

---

## Installation

> Requires Python 3.10+. Recommended: `uv`.

```bash
git clone https://github.com/hadasaelishyov/pytest-pipeline-mcp.git
cd pytest-pipeline-mcp
uv sync

# sanity check
uv run pytest
```

## Running

### Recommended: Run via an MCP client (Cursor / Claude Desktop / etc.)

Add this server to your MCP client configuration. The client will launch it automatically.

Example config:

```json
{
  "mcpServers": {
    "pytest-pipeline": {
      "command": "uv",
      "args": ["run", "pytest-pipeline-mcp"],
      "cwd": "C:\\path\\to\\pytest-pipeline-mcp"
    }
  }
}
```

> Restart your MCP client after updating the config.

### Debug: Run the server manually

```bash
uv run pytest-pipeline-mcp
```

## Optional configuration

Set environment variables for optional features:

- `OPENAI_API_KEY` — enables AI-enhanced generation and `fix_code`
- `GITHUB_TOKEN` — enables GitHub tools (PR/comments)

**PowerShell:**
```powershell
$env:OPENAI_API_KEY="..."
$env:GITHUB_TOKEN="..."
```

---

## End-to-End Pipeline

A core design principle of this server is **tool composability**. Each tool's output is structured to serve as input for the next, enabling seamless chained workflows:

```
┌──────────────┐     ┌─────────────────┐     ┌───────────┐     ┌──────────┐
│ analyze_code │ ──▶ │ generate_tests  │ ──▶ │ run_tests │ ──▶ │ fix_code  │
└──────────────┘     └─────────────────┘     └───────────┘     └──────────┘
       │                     │                     │                 │
       ▼                     ▼                     ▼                 ▼
   Code structure       Test code            Pass/fail +        Fixed code
   + warnings           ready to run         coverage           + verification
```

---

## Tool Reference

### Core Tools

| Tool | Purpose | Required | Optional |
|------|---------|----------|----------|
| `analyze_code` | Parse code via AST, validate syntax, report metrics | `file_path` or `code` | — |
| `generate_tests` | Generate pytest tests with evidence-based enrichment | `file_path` or `code` | `output_path`, `include_edge_cases`, `use_ai` |
| `run_tests` | Execute tests in isolated environment with coverage | `source_code`, `test_code` | — |
| `fix_code` | AI-assisted bug fixing with verification | `source_code`, `test_code` | `test_output`, `verify` |

### GitHub Tools

| Tool | Purpose | Required | Optional |
|------|---------|----------|----------|
| `analyze_repository` | Clone and analyze repo for test coverage gaps | `repo_url` | `branch`, `path_filter` |
| `get_repo_file` | Retrieve file content from a repository | `repo_url`, `file_path` | `branch` |
| `create_test_pr` | Create PR with generated tests | `repo_url`, `test_code`, `target_file` | `branch`, `title` |
| `comment_test_results` | Post test results on a PR | `repo_url`, `pr_number`, `test_results` | `coverage_report` |

---

## Architecture

```
pytest_pipeline_mcp/
├── server.py                  # MCP entry point (thin routing layer)
├── handlers/                  # Tool handlers (MCP ↔ services)
│   ├── core/                  # analyze, generate, run, fix
│   └── github/                # repo analysis, PR creation, comments
├── services/                  # Business logic (testable without MCP)
│   ├── base.py                # ServiceResult pattern, error codes
│   ├── code_loader.py         # Load Python code from file/string
│   ├── analysis.py            # AnalysisService
│   ├── generation.py          # GenerationService
│   ├── execution.py           # ExecutionService
│   ├── fixing.py              # FixingService
│   ├── github.py              # GitHubService
│   └── repository_analysis.py # RepositoryAnalysisService
└── core/                      # Pure logic (no framework dependencies)
    ├── analyzer/              # AST parsing, syntax validation
    ├── generators/            # Template + AI test generation
    │   ├── template.py        # Layer 1+2: template & evidence tests
    │   ├── ai.py              # Layer 3: AI enhancement
    │   └── extractors/        # Doctest, type, exception extractors
    ├── runner/                # pytest execution, coverage
    ├── fixer/                 # AI-powered bug fixing
    └── repo_analysis/         # Repository analysis models
```

**Design principles:**
- **Separation of concerns**: Server → Handlers → Services → Core
- **ServiceResult pattern**: All operations return success/failure with structured errors
- **Dependency injection**: Services accept dependencies via `__init__` for testability
- **Framework independence**: Core modules have no MCP or external framework dependencies

---

## Test Generation Pipeline

The generator uses a three-layer approach:

1. **Layer 1 (Fallback Smoke)**: used only when no evidence-based tests are found
2. **Layer 2 (Evidence)**: enrichment from concrete signals in the code:
   - Doctest examples → exact assertions
   - Type annotations → type checks and boundary values
   - Raise statements → `pytest.raises` tests
   - Naming conventions → boolean assertions for `is_*` / `has_*`
3. **Layer 3 (AI, optional)**: OpenAI-enhanced assertions with computed expected values

---

## Limitations

- Tests run in a subprocess with a 30-second timeout
- `fix_code` and AI enhancement require an OpenAI API key
- GitHub operations are subject to rate limits

## Security Notes

This server executes Python code. Do not run untrusted code without sandboxing. 
Store API keys securely and use minimal GitHub token permissions.