# Testing

From the repository root after dependency installation:

```bash
python -m pytest
python -m compileall -q code examples
python examples/safe_spending.py
```

`pytest.ini` selects `test_guardrails.py` by default. Its 12 tests exercise deterministic injection checks, schema validation, gross/net aliases, OCR plausibility handling, missing evidence, financial isolation, arithmetic consistency, localized amounts, explanations, spending changes, sanitization, and expense volatility.

## Historical scripts

The other files in `code/tests/` are retained development artifacts. Some load the dataset, consume local caches, call model APIs, or write results at import time. Do not run unrestricted test discovery without reviewing those side effects.

| Script group | Purpose |
|---|---|
| `smoke_test_phase1.py`, `smoke_test_phase2.py` | Early loader and extraction checks |
| `test_simulator.py`, `test_benchmark_12_cases.py` | Sample-based simulation regressions |
| `test_plan_generator.py`, `test_end_to_end.py` | Sample planning and pipeline experiments |
| `test_adv_gpt54.py`, `test_batch_gpt54.py`, `test_vision_gpt54.py`, `verify_model.py` | Explicit model integration experiments |

Run an individual script with `python code/tests/<script>.py` only after checking its requirements and side effects. Live scripts can incur provider charges and need model access.

## CI

GitHub Actions installs dependencies and runs syntax compilation, the selected guardrail suite, and the synthetic example on Python 3.11 and 3.13. It does not receive API keys or measure hidden challenge accuracy.

Local portfolio verification passed all 12 guardrail tests on Python 3.13. The full live dataset pipeline was not rerun as part of documentation preparation.
