# Pytest Generator MCP Server

A **Model Context Protocol (MCP)** server that generates **pytest** tests for Python modules using **static analysis** and an **evidence-first** workflow.  
AI steps can optionally refine tests and suggest fixes, but the server remains usable without API keys.

## Overview

Given a Python file (or a code string), the server can:

- **Analyze** code structure (functions/classes/methods), validate syntax, and report basic quality signals.
- **Generate** pytest tests using an *evidence-first* approach:
  - Extract **doctest-style examples** (when present)
  - Build **type-driven assertions** from annotations
  - Detect explicit **raised exceptions** and generate tests that trigger them
  - Add **boundary/edge cases** where relevant (e.g., empty input, zero/negative)
- **Run** generated tests and summarize results (with coverage enabled via project pytest config).
- **Optionally**:
  - Use OpenAI to **strengthen assertions** / add more targeted cases
  - Use OpenAI to propose **code fixes** and (optionally) verify by re-running tests
  - Integrate with GitHub (analysis + PR/comment workflows)

> Note: This project executes Python tests in a subprocess. Running untrusted code is inherently risky—see **Security notes**.

---

## Tools

### Core tools

| Tool | Purpose | Typical inputs | Typical outputs |
|------|---------|----------------|----------------|
| `analyze_code` | Parse and summarize code structure + warnings | `file_path` or `code` | JSON analysis summary |
| `generate_tests` | Generate pytest tests (templates + evidence + optional AI) | `file_path` or `code`, optional `output_path` | Test code (and optionally a saved file) |
| `run_tests` | Execute pytest against provided source + tests | `source_code`, `test_code` | Pass/fail summary + pytest output |
| `fix_code` | (Optional) AI-assisted fix loop, with optional verification | `source_code`, `test_code`, optional `test_output` | Suggested patch + verification result |

### GitHub tools (optional)

These tools require `GITHUB_TOKEN` in the environment (or equivalent configuration).

| Tool | Purpose |
|------|---------|
| `analyze_repository` | Clone + analyze a repository to identify modules that need tests |
| `create_test_pr` | Create a PR that adds/updates tests |
| `comment_test_results` | Comment summarized results back on a PR |

---

## Installation

### Requirements

- Python **3.10+**
- Recommended: **uv** (fast, reproducible installs)

### Install with uv (recommended)

```bash
git clone <https://github.com/hadasaelishyov/MCP_Server>
cd <your-repo-dir>

uv sync
uv run pytest -q
