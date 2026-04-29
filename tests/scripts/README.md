# Test Scripts

This directory stores scripts used for local smoke tests, integration checks, and manual acceptance verification.

## Naming Convention

Use lowercase ASCII names with hyphens:

```text
test-<scope>-<behavior>.<ext>
```

Examples:

```text
test-api-upload.ps1
test-api-search.ps1
test-rag-smoke.ps1
```

Rules:

- Keep scripts idempotent when possible.
- Do not store secrets or API keys in scripts.
- Read runtime configuration from environment variables or `.env`.
- Prefer scripts that can be run from the project root.
