# Security boundaries

Messages, image contents, request text, and event descriptions are untrusted evidence. Instructions inside them must not override challenge rules or directly choose a payment result.

Implemented controls include text sanitization, allowed message effect types, deterministic adversarial vetoes, strict extraction schemas, finite non-negative numeric checks, event-linked currency checks, and document arithmetic checks. Image identifiers are restricted and resolved beneath the configured image directory.

These controls reduce specific attack paths. They do not establish complete prompt-injection resistance or prove that extracted financial facts are authentic. A valid schema can still contain a wrong value.

## Credentials and data

Use `.env.example` as a template and keep the real `.env` local. Configuration reads the root `.env` with `override=True`, so file values override existing environment values. Never commit credentials, extraction caches, private conversation logs, or real financial records.

The full pipeline sends document images and message contents to the configured external model provider. Use only data you are permitted to process. No bank account integration or payment execution is implemented.

## Reporting

For a security issue, contact the repository owner through their GitHub profile using an available private channel. Do not put keys or private financial records into a public issue. This repository does not claim an audited security posture.
