# Detector experiments

Status: DRAFT; owner 04.01.

First question: do smoothing/stability windows in physical time reduce FPS/noise sensitivity?

Preserve detector 1.0.0 behavior and outputs. Predeclare a small duration set (proposal: 25/50/100/150 ms), rounding/minimum-window conventions and matched development comparisons.

Proposed development promotion tolerances: neither event median absolute error worsens by more than 5 ms; coverage falls by no more than two percentage points; one preselected weakness improves. These are engineering choices, not validated scientific standards; settle them before evaluation.

Freeze candidate and evaluate held-out data once under the evaluation protocol. A rejected candidate still produces a complete experiment. Do not add model families to rescue an unfavorable result.
