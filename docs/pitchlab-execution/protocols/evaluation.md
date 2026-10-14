# Evaluation

Status: DRAFT; owner 03.01.

Compare a frozen detector with a simple declared baseline through the same evaluator. Rows retain pitch/athlete/session/view/FPS/event/method/reference/prediction status and signed/absolute error.

Report detection coverage, median absolute error, bias, P90, within-10-ms fraction and explicit denominators. Missing predictions remain in accounting; unlabelable references are separate, never zero-error cases.

Measure derived FFS-to-BR interval error directly. Report human agreement and repeatability. Resample athletes where applicable; with three held-out athletes, population uncertainty is unstable and must be described as such.

Downsampling preserves source time correspondence; it does not reproduce real low-FPS motion blur. Label oracle inputs, idealized geometry and simulated landmarks explicitly.

Generate reports from saved tables. Reconcile the recorded RQ2 ordering discrepancy before publishing it.
