"""EXERCISE 5b (Ziyu): the worker task. RQ calls run_analysis_job(job_id).

TODO(ziyu): implement. Tests: tests/exercises/test_ex5_worker_and_jobs.py

Transaction boundaries matter here (the defense checklist asks about them):

1. Claim: in one transaction, load the job with SELECT ... FOR UPDATE.
   If it is missing or its status is not "queued", return (a duplicate or stale
   queue message: doing nothing is correct). Otherwise transition to RUNNING,
   set worker_id (socket.gethostname() + ":" + str(os.getpid())), and commit.
2. Work: OUTSIDE any transaction, resolve the video file with
   get_storage().path_for(video.storage_key) and call
   get_analyzer().analyze(path, athlete.throwing_hand).
   The analysis can take minutes; never hold a DB transaction or row lock that long.
3a. Success: in ONE transaction, delete any pitches already stored for this job
    (a previous attempt may have written some), insert Pitch/Event rows from the
    AnalysisOutput, fill video.fps/width/height if they are NULL, transition to
    SUCCEEDED, and commit. Either everything is saved or nothing is.
3b. Failure (any Exception from step 2 or 3a): roll back, reload the job, call
    handle_failure(job, str(exc), now, settings.retry_base_seconds,
    settings.retry_cap_seconds), and commit. If it returned a delay, call
    enqueue_analysis(job_id, delay) AFTER the commit. Do not re-raise: the failure is
    recorded in the database, which is the source of truth.

Use app.db.session_factory()() to open sessions and datetime.now(timezone.utc) for now.
"""


def run_analysis_job(job_id: int) -> None:
    raise NotImplementedError("Exercise 5b: run_analysis_job()")
