# Performance benchmarking

Status: DRAFT; owner 07.02/07.03.

Backend-only: existing fake analyzer, fixed service time, 1/2/4 workers, three repetitions per condition; same user count, run duration, hardware and configuration. Drain queues between runs; include failures and backlog growth. Report API latency separately from queue wait and job runtime.

Real inference: three fixed permitted clips with durations/resolution/FPS/configuration/hardware; repeat consistently and state warm/cold effects. Never call fake-analyzer throughput video-processing throughput.

For an optimization, show representative baseline, identified bottleneck, one change and matched comparison. Retaining the original after finding no benefit is valid evidence.
