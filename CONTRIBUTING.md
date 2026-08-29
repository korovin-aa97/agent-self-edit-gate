# Contributing

Thank you for helping make self-editing agents safer and more predictable.

## Before opening a change

- For security vulnerabilities, use private reporting described in
  [SECURITY.md](SECURITY.md).
- For behaviour changes, open an issue describing the security invariant,
  compatibility impact, and test plan.
- Keep the project narrow: no hosted service, telemetry, LLM policy decisions,
  or general fleet orchestration.

## Development setup

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are recommended.

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest --cov=selfedit_gate --cov-report=term-missing
uv build
```

Every behaviour change needs a regression test and a changelog entry. Public
interfaces are typed. Policy decisions must remain deterministic and fail
closed. Do not weaken deny precedence or the honest external-boundary statement.

By submitting a contribution, you agree that it is licensed under Apache-2.0.
Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
