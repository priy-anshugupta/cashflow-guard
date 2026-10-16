# Known limitations

Cashflow Guard is a challenge prototype. The following boundaries matter when assessing or extending it.

| Area | Practical limitation |
|---|---|
| Money representation | Python floats and two-decimal output rounding are used rather than decimal or integer minor-unit accounting. Currency-specific precision is not modeled. |
| Forecast assumptions | Recurrence, variable spending, and message effects depend on heuristics and the supplied history. Missing obligations cannot be inferred reliably. |
| Model evidence | Strict schemas and arithmetic checks do not prove extraction accuracy or document authenticity. |
| OCR plausibility | Some implausible extracted values are filtered to zero during reconstruction; the guardrail test records that behavior. A production version should stop or request review for uncertain essential expenses. |
| Earliest payment date | The date calculator includes a desired-completion-window fallback. Review it before claiming every returned date is safe across the full forecast horizon. |
| Independent requests | Requests are assessed independently; outputs are not a joint budget for executing every purchase together. |
| Reproducibility | Cached evidence can stabilize a replay, but live model responses may vary. Cache entries are keyed by identifiers without content-based invalidation. |
| Output validation | Checks cover a subset of structural and contract conditions. The CLI writes CSVs before validation, so failed runs may leave files behind. |
| Usage estimates | Hardcoded price assumptions and combined model-token accounting can become inaccurate, particularly with different vision and NLP models. |
| Test coverage | Default CI runs 12 guardrail tests. Passing them does not imply all sample expectations or hidden evaluations pass. |
| Deployment | No live bank connector, identity checks, payment execution, or production monitoring is implemented. |

The reported competition rank is an author-supplied result. It is not a percentage accuracy measure or a guarantee for other financial datasets. Review and expand the financial regression suite before using this code beyond the challenge.
