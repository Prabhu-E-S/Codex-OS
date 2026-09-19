# Demo Project — Python Calculator

This is the **Codex OS demonstration target** — a deliberately buggy Python calculator project designed to showcase the full autonomous agent pipeline.

## Purpose

Point Codex OS at this repository path to run a live demonstration:

- **Architect Agent** — Analyzes the codebase, identifies structure and gaps
- **Builder Agent** — Implements fixes (division-by-zero guard, input validation)
- **Tester Agent** — Runs pytest, reports pass/fail
- **Breaker Agent** — Attempts to crash the fixed code adversarially
- **Security Agent** — Scans for reliability and security issues
- **Evaluation** — Computes an Engineering Score across 6 dimensions

## Intentional Bugs

| Function | Bug |
|----------|-----|
| `divide(a, b)` | No guard against `b == 0` → raises `ZeroDivisionError` |
| `sqrt(n)` | No guard against negative `n` → `math domain error` |
| `add(a, b)` | No type validation → silently concatenates strings |
| `factorial(n)` | No guard against negative integers |

## Running Tests

```bash
cd demo-project
pip install -r requirements.txt
pytest tests/ -v
```

## Expected Codex OS Engineering Score

After one autonomous iteration:
- **Correctness**: ~60% (some tests failing initially)
- **Security**: ~50% (missing input validation)
- **Maintainability**: ~70% (clean structure, poor guards)

After two iterations with Builder fixing issues:
- **Overall score**: ~80–90%
