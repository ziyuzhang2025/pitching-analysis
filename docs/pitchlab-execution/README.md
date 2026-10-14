# Pitch Lab execution guide

Start here. This folder is the authoritative execution guide for a local pitching-event review application and demonstrable backend SWE capability. The current priority is to build and understand the backend first, using the fake analyzer to separate backend correctness from computer-vision accuracy.

## Read in this order

1. [Project contract](01-project-contract.md)
2. [Verified current state](02-current-state.md)
3. [Backend architecture](05-backend-architecture.md): components, ownership, data flow and implementation gaps
4. [Backend execution contract](06-backend-execution-contract.md): full task order, invariants and milestone gate
5. [Progress](progress/status.md)
6. [Active task](tasks/active.md)
7. The protocols and evidence linked by that task

Use [milestones](03-milestones.md) for dependencies and [backend capability rubric](04-backend-capability-rubric.md) for assessment.

## Authority and scope

Direct user instructions control the work. The project contract defines scope; protocols define scientific rules; the active task defines currently scheduled work. Existing [backend exercise specifications](../backend_exercises.md) and source docstrings define exercise interfaces. Record conflicts instead of silently changing contracts.

This folder replaces the earlier [long execution proposal](../superpowers/plans/2026-10-12-pitchlab-execution.md) as the working guide. The proposal remains background, not a second task queue. Prior visual summaries are historical.

The current execution order is: short evidence preflight → backend completion (M5) → research validation (M1–M4) → persistent review app (M6) → release evidence (M7). The backend track is fully specified at the task-gate level in the execution contract. The active task is the only task authorized for execution; later task files remain OUTLINE until their dependencies are complete and their interfaces are rechecked against the changed source. Protocols are DRAFT until their owning task validates and freezes them. File existence never means implementation is complete.

## Start an agent with this context

> Read docs/pitchlab-execution/README.md and follow its reading order, including 05-backend-architecture.md and 06-backend-execution-contract.md before execution. Explain the backend's request-to-result flow and distinguish implemented components from stubs. Then work only on the task referenced in tasks/active.md. Before a backend change, state the owning layer, invariant, expected failure and verification command. Preserve the project contract and ownership rules. Verify the actual checkout before relying on recorded state. Record verification and handoff evidence; never promote an outline, passing fake-analyzer test or generated file into a broader claim. Coach and review Ziyu's backend exercise implementation unless I explicitly authorize you to write that specific exercise.

## Maintenance

Keep completed tasks at their original paths. Update their status and evidence links. Maintain one active coding task. Evidence logs are append-only; corrections explicitly supersede earlier entries. Large/private data stay outside this folder. Do not duplicate scientific definitions, architecture decisions, or ownership records.
