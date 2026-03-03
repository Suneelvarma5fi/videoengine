"""
Upload route — accepts a video file and creates a new job.

POST /api/upload
  multipart/form-data: file=<video>
  → { job_id, filename, status }
"""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter()

UPLOADS_DIR = Path("uploads")
JOBS_DIR    = Path("jobs")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    job_id   = str(uuid.uuid4())
    job_dir  = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    video_path = job_dir / f"input{suffix}"
    content    = await file.read()
    video_path.write_bytes(content)

    status = {
        "job_id":    job_id,
        "filename":  file.filename,
        "video":     str(video_path),
        "status":    "uploaded",
    }
    (job_dir / "status.json").write_text(json.dumps(status, indent=2))

    return status
