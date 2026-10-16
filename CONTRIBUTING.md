# Contributing

Start with the [architecture](docs/architecture.md), [decision policy](docs/decision-policy.md), and [known limitations](docs/limitations.md). Keep the original HackerRank input/output contract intact when changing the challenge pipeline.

1. Create a branch describing the change.
2. Keep model extraction outside deterministic financial calculations.
3. Add focused regression coverage for changed financial behavior using synthetic data where possible.
4. Run `python -m pytest`, `python -m compileall -q code examples`, and `python examples/safe_spending.py`.
5. Explain the trigger, resulting behavior, test evidence, and remaining limitations in the pull request.

Do not commit API keys, real financial records, private logs, caches, or generated submission archives. Do not silently regenerate historical usage reports when making documentation changes. Review dataset and API side effects before running historical integration scripts.

This checkout has no general reuse license; see [provenance](docs/provenance.md) before distributing adaptations.
