# Cashflow Guard implementation

This directory contains the Python agent built for HackerRank Orchestrate: Buy or Wait?. Start with the [project README](../README.md) for an overview, achievement, example, and setup.

Run commands from the repository root:

```bash
python -m pip install -r code/requirements.txt
python code/main.py --help
python -m pytest
```

For the full dataset pipeline, configure `.env` using `.env.example`, then run `python code/main.py`. Image extraction requires model access or validated local cache entries. The cache is excluded from Git.

| Directory | Responsibility |
|---|---|
| `data/` | Input schemas, sanitization, loading, and relational context |
| `extraction/` | Validated image amounts, message effects, currency conversion, and caching |
| `engine/` | State reconstruction, daily simulation, safe amount, dates, schedules, spending changes, and validation |
| `output/` | Financial explanations assembled from evaluated context |
| `tests/` | Default guardrail suite and explicitly run historical experiments |
| `evaluation/` | Starter evaluation entry point and historical report copy |

The authoritative run report is at root `evaluation/usage_report.md`. The confidence helper is an experimental heuristic; the main CSV pipeline does not emit confidence values.

Read [testing](../docs/testing.md), [decision policy](../docs/decision-policy.md), and [limitations](../docs/limitations.md) before changing financial behavior.
