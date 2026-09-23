# Architecture Decision Records

Ziyu writes these, in his own words, about half a page each, using `0000-template.md`.

1. `0001-job-queue.md`: Redis + RQ vs Celery vs a Postgres table with `SKIP LOCKED`
2. `0002-idempotency.md`: unique constraints, the partial unique index, and `Idempotency-Key`
3. `0003-versioned-results.md`: why results carry `detector_version`, and how backfill works
4. `0004-storage-interface.md`: local disk behind an interface; how S3 would slot in
5. `0005-analyzer-as-library.md`: why the analyzer is called as a library/CLI, not a service
