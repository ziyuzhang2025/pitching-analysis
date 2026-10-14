# Dataset splits

Status: DRAFT; owner 03.01.

Assign athlete groups before tuning/labeling. All sessions, views, duplicated clips and frame-rate derivatives of an athlete remain in one split. P01 and existing tuned footage remain development.

Verify split manifest consistency with actual evaluation rows, including derived-clip identity and input hashes. Reject subject leakage.

Record every held-out evaluation with frozen source/configuration and purpose. Do not repeatedly tune against the same held-out results. A failed result narrows the claim or requires a new justified evaluation design.
