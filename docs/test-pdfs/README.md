# Test PDFs

This directory stores PDF files used for local and integration testing.

## Naming Convention

Use lowercase ASCII names with hyphens:

```text
YYYYMMDD-domain-short-description-vNN.pdf
```

Examples:

```text
20260429-rag-product-intro-v01.pdf
20260429-milvus-search-notes-v01.pdf
20260430-embedding-api-spec-v02.pdf
```

Rules:

- Keep filenames lowercase.
- Use hyphens instead of spaces or underscores.
- Use `v01`, `v02`, `v03` for revisions.
- Do not put user-uploaded runtime files here. Runtime uploads belong in `data/uploads/`.
