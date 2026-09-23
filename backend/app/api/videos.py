"""EXERCISES 3b and 4 (Ziyu): video upload, lookup, and starting an analysis.

TODO(ziyu): implement the three handlers. Tests:
tests/exercises/test_ex3_sessions_videos_api.py and test_ex4_idempotency.py

POST /sessions/{session_id}/videos   multipart: file=<video>, view=<CameraView, optional>
    - 404 if the session does not exist.
    - 415 (code "unsupported_media_type") if the file extension is not in
      settings.allowed_video_extensions.
    - Stream the upload to storage with storage.save_stream(file.file, suffix,
      settings.max_upload_bytes) (it raises 413/400 itself).
    - Use app.services.idempotency.find_or_create_video(...).
      New video -> 201 VideoOut. Same bytes already uploaded to this session -> 200 with
      the EXISTING VideoOut, and delete the duplicate file you just stored.

GET /videos/{video_id} -> 200 VideoOut, 404 if missing.

POST /videos/{video_id}/analyze      optional header: Idempotency-Key
    - 404 if the video does not exist.
    - version = get_analyzer().version; max_attempts = settings.job_max_attempts
    - Use app.services.idempotency.get_or_create_job(...).
      New job -> commit, THEN enqueue_analysis(job.id), and return 202 JobOut.
      Existing job -> 200 JobOut, and do NOT enqueue again.
    - Same Idempotency-Key reused for a different video -> 409 (Conflict).
Tip: set the status code with fastapi.Response (response.status_code = 200).
"""

from fastapi import APIRouter, Depends, File, Form, Header, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotImplementedYet
from app.schemas import CameraView, JobOut, VideoOut
from app.storage import Storage, get_storage

router = APIRouter(tags=["videos"])


@router.post("/sessions/{session_id}/videos", response_model=VideoOut,
             status_code=status.HTTP_201_CREATED)
def upload_video(
    session_id: int,
    response: Response,
    file: UploadFile = File(...),
    view: CameraView | None = Form(default=None),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    raise NotImplementedYet("Exercise 3b: POST /sessions/{id}/videos")


@router.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    raise NotImplementedYet("Exercise 3b: GET /videos/{id}")


@router.post("/videos/{video_id}/analyze", response_model=JobOut,
             status_code=status.HTTP_202_ACCEPTED)
def analyze_video(
    video_id: int,
    response: Response,
    idempotency_key: str | None = Header(default=None, max_length=100),
    db: Session = Depends(get_db),
):
    raise NotImplementedYet("Exercise 4: POST /videos/{id}/analyze")
