"""
Jobs routes — transcription, rendering, download.

GET  /api/jobs/{job_id}              → job status
POST /api/jobs/{job_id}/transcribe   → extract audio + run WhisperX
GET  /api/jobs/{job_id}/transcript   → word-level JSON
GET  /api/templates                  → list available templates
POST /api/jobs/{job_id}/render       → burn subtitles into video
GET  /api/jobs/{job_id}/download     → stream final MP4
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.audio_extractor import extract_audio
from core.transcriber import Transcriber
from core.ass_exporter import export_ass
from core.video_renderer import burn_subtitles, check_libass
from subtitle_engine.engine import process as subtitle_process
from subtitle_engine.models import InputWord
from transcriber_models.config import ExtractorConfig

router = APIRouter()

JOBS_DIR      = Path("jobs")
TEMPLATES_DIR = Path("templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job_dir(job_id: str) -> Path:
    d = JOBS_DIR / job_id
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return d


def _read_status(job_id: str) -> dict:
    return json.loads((_job_dir(job_id) / "status.json").read_text())


def _write_status(job_dir: Path, data: dict) -> None:
    (job_dir / "status.json").write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Background pipeline helpers
# ---------------------------------------------------------------------------

def _run_transcription(job_id: str, job_dir: Path, video_path: str) -> None:
    status = _read_status(job_id)
    try:
        status["status"] = "extracting_audio"
        _write_status(job_dir, status)

        audio_path = job_dir / "audio.wav"
        extract_audio(video_path, audio_path)

        status["status"] = "transcribing"
        _write_status(job_dir, status)

        transcriber = Transcriber(ExtractorConfig.default())
        transcript  = transcriber.transcribe(audio_path)

        transcript_path = job_dir / "transcript.json"
        transcript_path.write_text(transcript.to_json())

        status["status"]    = "transcribed"
        status["transcript"] = str(transcript_path)
        status["word_count"] = transcript.metadata.word_count
        _write_status(job_dir, status)

    except Exception as exc:
        status["status"] = "error"
        status["error"]  = str(exc)
        _write_status(job_dir, status)


def _run_render(
    job_id: str,
    job_dir: Path,
    video_path: str,
    template_name: str,
    block_config_override: Optional[Dict[str, Any]],
    video_width: int,
    video_height: int,
) -> None:
    status = _read_status(job_id)
    try:
        transcript_path = job_dir / "transcript.json"
        if not transcript_path.exists():
            raise RuntimeError("Transcript not found. Run transcription first.")

        raw = json.loads(transcript_path.read_text())
        words = [
            InputWord(
                text=w["text"],
                start=w["start"],
                end=w["end"],
                duration=w["duration"],
                confidence=w.get("confidence"),
            )
            for w in raw["words"]
        ]

        status["status"] = "building_subtitles"
        _write_status(job_dir, status)

        layout = subtitle_process(
            words,
            template_name=template_name,
            block_config_override=block_config_override,
        )

        ass_path = job_dir / "subtitles.ass"
        export_ass(layout, ass_path, video_width=video_width, video_height=video_height)

        status["status"] = "rendering"
        _write_status(job_dir, status)

        output_path = job_dir / "output.mp4"
        burn_subtitles(video_path, ass_path, output_path)

        status["status"] = "done"
        status["output"]  = str(output_path)
        _write_status(job_dir, status)

    except Exception as exc:
        status["status"] = "error"
        status["error"]  = str(exc)
        _write_status(job_dir, status)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return _read_status(job_id)


@router.post("/jobs/{job_id}/transcribe")
def transcribe_job(job_id: str, background_tasks: BackgroundTasks):
    job_dir = _job_dir(job_id)
    status  = _read_status(job_id)

    if status["status"] not in ("uploaded", "error"):
        return {"message": f"Job already in state '{status['status']}'", **status}

    video_path = status.get("video")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=400, detail="Video file missing from job")

    background_tasks.add_task(_run_transcription, job_id, job_dir, video_path)
    status["status"] = "queued"
    _write_status(job_dir, status)
    return {"message": "Transcription started", "job_id": job_id}


@router.get("/jobs/{job_id}/transcript")
def get_transcript(job_id: str):
    job_dir = _job_dir(job_id)
    transcript_path = job_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not ready yet")
    return json.loads(transcript_path.read_text())


@router.get("/templates")
def list_templates():
    if not TEMPLATES_DIR.exists():
        return {"templates": []}
    names = [f.stem for f in TEMPLATES_DIR.glob("*.json")]
    return {"templates": sorted(names)}


class RenderRequest(BaseModel):
    template_name: str = "center_minimal_v1"
    block_config_override: Optional[Dict[str, Any]] = None
    video_width: int = 1080
    video_height: int = 1920


@router.post("/jobs/{job_id}/render")
def render_job(job_id: str, req: RenderRequest, background_tasks: BackgroundTasks):
    if not check_libass():
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is missing libass. Install via `brew install ffmpeg`.",
        )

    job_dir = _job_dir(job_id)
    status  = _read_status(job_id)

    if status["status"] not in ("transcribed", "done", "error"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot render: job is in state '{status['status']}'",
        )

    video_path = status.get("video")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=400, detail="Video file missing from job")

    background_tasks.add_task(
        _run_render,
        job_id,
        job_dir,
        video_path,
        req.template_name,
        req.block_config_override,
        req.video_width,
        req.video_height,
    )
    status["status"] = "rendering_queued"
    _write_status(job_dir, status)
    return {"message": "Render started", "job_id": job_id}


@router.get("/jobs/{job_id}/download")
def download_output(job_id: str):
    job_dir    = _job_dir(job_id)
    status     = _read_status(job_id)
    output_path = status.get("output")

    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Output video not ready yet")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"{job_id}_subtitled.mp4",
    )
