# Release acceptance

Status: NOT RUN.

- [ ] Real permitted clip completes upload → analysis → review → correction → export.
- [ ] Service restart preserves selected version, artifacts and correction history.
- [ ] Malformed input, no detected pitches and analysis failure have explicit outcomes.
- [ ] Concurrency/retry/version invariants verified.
- [ ] Measurements, generated tables and limitations agree.
- [ ] Root and full backend required checks pass on the release revision.
- [ ] Local exposure and data handling checked; no claim of multi-user security.
- [ ] Backup restored in disposable environment; shutdown/recovery rehearsed.
- [ ] Fake-worker scaling and real-inference timings labeled separately.
- [ ] Ownership and capability defense recorded.

Attach revision, environment, commands and observations. No check is passed by writing documentation about intended behavior.
