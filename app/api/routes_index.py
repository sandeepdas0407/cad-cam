import threading

from fastapi import APIRouter

from app.config import DB_PATH, get_settings
from app.ingestion.pipeline import get_status, run_pipeline

router = APIRouter()
_lock = threading.Lock()


def _run_in_background():
    config = get_settings()
    run_pipeline(config, DB_PATH)


@router.post("/api/reindex")
def reindex():
    if not _lock.acquire(blocking=False):
        return {"status": "already_running"}
    try:
        thread = threading.Thread(target=_run_and_release, daemon=True)
        thread.start()
    except Exception:
        _lock.release()
        raise
    return {"status": "started"}


def _run_and_release():
    try:
        _run_in_background()
    finally:
        _lock.release()


@router.get("/api/index/status")
def index_status():
    return get_status()


@router.get("/api/folders")
def folders():
    config = get_settings()
    return {"watched_folders": [str(p) for p in config.get("watched_folders_resolved", [])]}
