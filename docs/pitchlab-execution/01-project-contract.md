# Project contract

Status: release scope and backend-first execution order accepted; core backend exercise implementation has not begun through this guide.

## Outcome

A local user can select/upload a pitching session, estimate visible foot contact and approximate release, inspect evidence, correct events, export a report, and retrieve the same results after restart.

The career outcome is inspectable engineering and research work that Ziyu can explain and defend. Completion has two gates: the system works, and Ziyu demonstrates understanding. Neither gate implies the other.

## Release boundaries

- Retain Streamlit, existing detector scripts and FastAPI/PostgreSQL/Redis/RQ scaffold.
- Initial study targets original side-view footage; unsupported conditions receive explicit limitations.
- No performance-improvement, injury-risk or clinical conclusions.
- Preserve raw predictions, independently collected reference annotations and user corrections separately.
- Keep result and input provenance. Legacy keys remain readable with explicit legacy semantics.
- Heuristic quality labels are not calibrated probabilities.
- Local release only. Any shared/network deployment requires authentication, resource authorization and security review first. Verify actual bind addresses; "local" is not an assumed property of Docker.
- Defer new model families, frontend rewrites, billing, multi-camera reconstruction and new sensors.

## Ownership and agent behavior

Follow [backend ownership](../backend_ownership.md) and [exercise instructions](../backend_exercises.md): Ziyu implements exercises; agents explain and review unless specifically authorized to implement one. Record assistance honestly. Do not write defense answers and then treat their repetition as understanding.

Agents may inspect code, refine routine choices within the active task, and perform scoped checks. Implementation requires a user instruction to execute the task; creating this guide does not authorize all future tasks. Do not infer permission to deploy, publish data, recruit participants, erase databases or push changes from a task outline.

Before changing a shared function, inspect callers and affected tests. Preserve unrelated changes. When evidence conflicts with a plan, record it and resolve the narrow conflict. When blocked, finish independent in-scope work and state the exact dependency.

## Execution priority

Build the backend before detector experiments and full UI integration. Use FakeAnalyzer for backend work so API, persistence, concurrency and recovery can be tested deterministically without claiming real-video accuracy. Research validation remains necessary before real analyzer results can support scientific claims.

The backend-first decision does not bypass evidence. A short preflight must record revision, test availability, unfinished components and service blockers. Backend work may then proceed while missing historical input provenance remains an explicit research-baseline blocker.

## Work budget

Default four focused hours/week, reduced around exams. One active coding task; data collection may continue asynchronously. Re-estimate after every milestone. No automatic commitment to a calendar deadline or unsupported accuracy target.
