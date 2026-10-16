# Reproducibility and usage

## Configuration

Paths are relative to the repository, not the shell's working directory. Configuration loads root `.env` with override enabled. `VISION_MODEL`, `NLP_MODEL`, and `DEFAULT_MODEL` default to the model names in `.env.example`; the vision and NLP values select their respective extraction models.

## Execution modes

With an API key present, the main pipeline requests fresh evidence by setting `force_live=True`. `--require-live` additionally requires a key and rejects message-classification fallback. Without a key, validated OCR cache entries are required; a fresh checkout does not have them. Message classification supports deterministic fallback under its configured conditions.

The cache lives in ignored `cache/`. It stores validated evidence, including source provenance. It is keyed by identifiers rather than document-content hashes, so clear or segregate it when changing datasets. Do not publish caches containing private financial information.

## Reports and artifacts

The checked-in `evaluation/usage_report.md` describes a recorded challenge run, not a fresh benchmark. Its original timestamp, token counts, and cost estimate are retained. The `code/evaluation/usage_report.md` file is the historical copy used in the solution package.

Rerunning the full CLI overwrites `output.csv`, `dataset/output.csv`, and the default report. Use `--report` to preserve the old report. Sample mode always chooses `sample_output.csv`; the generic `--output` argument is not applied in sample mode.

The reporter combines tokens from both extraction components and applies a hardcoded pricing branch based on the vision model name. Treat its dollars as estimates under the original assumptions, not current provider pricing. For new runs with different models, calculate each component's costs separately using verified rates.

The deterministic core makes no model calls. Its results still depend on the accepted evidence, data, code version, and numerical rounding. The synthetic example gives a small repeatable entry point without a live provider.
