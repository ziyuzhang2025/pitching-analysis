# Backend ownership log

Records who wrote which part of `backend/`, so the portfolio claims stay honest.
Update it when an exercise is finished.

| Part | Author | Date | Notes (what I learned / defense-check answers) |
|---|---|---|---|
| Infrastructure: config, db, logging, errors, pagination, storage, queue, analyzers, app factory | Claude | 2026-09-23 | Scaffold |
| Worked example: `Athlete` model, migration 0001, `/athletes`, `/health`, `/version` | Claude | 2026-09-23 | Pattern to copy |
| Tooling: `worker/run.py`, Docker, compose, CI, load test, progress script, test fixtures | Claude | 2026-09-23 | |
| Exercise tests (`tests/exercises/`) and specs (docstrings) | Claude | 2026-09-23 | Validated against a private reference implementation (all 72 pass); a deliberately naive idempotency implementation fails the race test |
| Ex 1 models + migration 0002 | Codex, explicitly delegated by Ziyu | 2026-10-19 | System gate verified; Ziyu's independent defense remains pending, so this is not evidence that Ziyu authored the implementation |
| Ex 2 state machine + retry | Ziyu | | |
| Ex 3 sessions + upload | Ziyu | | |
| Ex 4 idempotency | Ziyu | | |
| Ex 5 worker task + jobs API | Ziyu | | |
| Ex 6 reaper | Ziyu | | |
| Ex 7 results + backfill | Ziyu | | |
| ADRs 1–5 | Ziyu | | |

## "Write it for me" exceptions

(Anything Claude wrote in an exercise at Ziyu's explicit request goes here.)

- 2026-10-19 — Ziyu explicitly replied “do it” after Codex stated that Exercise 1 had
  been left for Ziyu. Codex implemented the five pipeline models, exports, and migration
  `0002`. This delegation is attributed and does not satisfy the capability gate.
