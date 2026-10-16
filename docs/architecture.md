# Architecture

`code/main.py` coordinates the pipeline. It loads CSVs into typed models, creates a `DataRepository`, extracts evidence, reconstructs a ledger per request, evaluates payment candidates, builds explanations, and writes CSV and usage artifacts.

## Evidence boundary

`extraction/vision.py` returns schema-validated document amounts. When supplied, gross, deductions, and net values are checked for internal arithmetic consistency. Event-linked currencies constrain accepted extraction. `extraction/messages.py` classifies messages into allowed effects and applies deterministic safety vetoes. Neither model produces the final payment decision.

## Deterministic boundary

`engine/state_reconstructor.py` turns events and accepted amendments into home-currency cash-flow entries. `cashflow_simulator.py` processes each day with debits before credits and records the lowest reserve cushion. `safe_amount.py` caps that cushion at the request amount and rounds to two decimal places. `earliest_date.py` searches projected dates; `plan_generator.py` evaluates and ranks payment candidates.

## Output boundary

`output/explanation.py` builds text from the evaluated financial context. `engine/validator.py` checks output fields against the request table. The CLI currently writes output before validation; callers should only consume artifacts after a successful exit.

## Design record

`PRD.md` is the original design document. It records intent and may differ from current behavior. This guide and the source describe the present implementation. `engine/confidence.py` is a heuristic helper rather than a calibrated probabilistic model and is not part of the main output contract.
