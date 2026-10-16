# Data contract

The pipeline reads files from root `dataset/`. Use participant-facing data only. The complete authoritative schema is in [problem_statement.md](../problem_statement.md).

| File | Role |
|---|---|
| `financial_profiles.csv` | Home currency, available balance, reserve, protected spending, and preferences |
| `financial_events.csv` | Historical and prospective events, cash states, and lifecycle links |
| `requests.csv` | Evaluation purchases and deadlines |
| `sample_requests.csv` | Public examples with completed answer fields |
| `request_payment_options.csv` | Seller schedules and available payment methods |
| `exchange_rates.csv` | Fixed rates indexed by date and currency direction |
| `messages.csv` | Optional evidence, sometimes linked to a particular event |
| `images.csv` | Image metadata and event links |
| `media/images/<image_id>.png` | Referenced document images |

Join by supplied identifiers, including `user_id`, `request_id`, and `related_event_id`. Blank message event links do not imply a one-to-one transaction. Linked event identifiers alone do not establish cash settlement.

Never treat a missing image amount as a free expense. Required evidence may cause a run to fail. Foreign-currency conversions use the supplied settlement-date rate in the specified direction; no live rate service is used.

Output must contain one row per evaluation request and the exact eight columns shown in the root README. The full-run CLI also overwrites `dataset/output.csv`; this is implementation behavior, so save artifacts before rerunning.
