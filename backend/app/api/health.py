"""Health and version endpoints (agent-written)."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.analyzers import get_analyzer
from app.config import get_settings
from app.db import get_db
from app.queue import get_redis
from app.schemas import HealthOut, VersionOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> JSONResponse:
    """200 when Postgres and Redis both answer; 503 otherwise (for load balancers)."""
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False
    try:
        redis_ok = bool(get_redis().ping())
    except Exception:
        redis_ok = False
    ok = database_ok and redis_ok
    body = HealthOut(status="ok" if ok else "degraded", database=database_ok, redis=redis_ok)
    return JSONResponse(status_code=200 if ok else 503, content=body.model_dump())


@router.get("/version", response_model=VersionOut)
def version() -> VersionOut:
    settings = get_settings()
    return VersionOut(api_version=__version__, detector_version=get_analyzer().version,
                      analyzer=settings.analyzer)
