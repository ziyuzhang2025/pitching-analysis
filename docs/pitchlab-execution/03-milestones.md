# Milestones and evidence gates

All milestones currently NOT STARTED. Detailed tasks are in tasks/. Stable milestone IDs are retained for links; the execution order is intentionally not numeric.

## Authoritative execution order

1. Evidence preflight: inspect the checkout, run safe root checks and record blockers.
2. M5 backend: follow the [backend execution contract](06-backend-execution-contract.md) through the deterministic fake-analyzer request-to-result path and reliability gates.
3. M1–M4 research: establish reproducibility, independent references, real-video evaluation and one controlled detector experiment.
4. M6 integration: persist review artifacts/corrections and connect Streamlit to the backend.
5. M7 release: acceptance, measured performance, case study and ownership defense.

Backend work can proceed without a complete research baseline because FakeAnalyzer is deterministic and makes no accuracy claim. RealAnalyzer integration, research conclusions and release claims still depend on M1–M4.

| ID | Outcome | Depends on | System gate | Capability gate |
|---|---|---|---|---|
| M1 | Honest, reproducible baseline | None | Saved manifest; claims consistent across old/new outputs; regression checks | Explain supported observations versus proxies |
| M2 | Independent annotation | M1 | Blind labeling, durable records, ambiguity rules | Explain label bias and reference limits |
| M3 | Real-video evaluation | M2 + recordings | Complete denominators, agreement, leakage checks, generated report | Defend unit of analysis and split |
| M4 | One detector experiment | M3 development evidence | Frozen comparison and recorded accept/reject outcome | Explain tradeoff and failed hypotheses |
| M5 | Working, inspectable backend | Evidence preflight | Exercises plus concurrency, security-boundary and operations checks using FakeAnalyzer | Diagnose injected failures and defend design |
| M6 | Persistent review app | M4 decision + M5 | Real session, artifacts and corrections survive restart | Trace a result across system boundaries |
| M7 | Release evidence | M6 | Acceptance report, reproducibility, measured performance | Live technical defense with honest ownership |

M4 can retain the baseline detector: a trustworthy negative result closes the research task.

## Capacity

Earlier core estimate: 102–152 hours. Newly explicit observability, SQL/API, security and operations work adds a provisional 16–28 hours: total 118–180 hours, about 30–45 working weeks at four hours/week. These estimates overlap imperfectly; re-estimate using actual task durations. Participant scheduling, exams and long unattended runs extend elapsed time.

The first backend evidence increment is Exercise 1; the first research-valid release increment is M1. Neither requires waiting for M7 to show progress.

## First four backend-first working weeks

1. Complete models and migration; explain every database constraint.
2. Implement and test the job state machine and retry policy.
3. Implement sessions and streaming uploads.
4. Implement race-safe idempotency and trace the first queued fake-analysis request.

If this exceeds capacity, finish the current deliverable before adding work. No tuning on held-out outcomes.
