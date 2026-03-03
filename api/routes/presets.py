"""
Presets routes — save and load user-defined template configurations.

GET    /api/presets           → list saved presets
POST   /api/presets           → save a preset (body: {name, ...config})
DELETE /api/presets/{name}    → delete a preset
"""
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()

PRESETS_DIR = Path("presets")

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\- ]{1,64}$")


def _safe_filename(name: str) -> str:
    """Sanitize preset name to a filesystem-safe slug."""
    return name.strip().replace(" ", "_")


@router.get("/presets")
def list_presets():
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    presets = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            presets.append(data)
        except json.JSONDecodeError:
            pass
    return {"presets": presets}


class PresetPayload(BaseModel):
    name: str
    config: Dict[str, Any]


@router.post("/presets")
def save_preset(payload: PresetPayload):
    if not _SAFE_NAME.match(payload.name):
        raise HTTPException(
            status_code=400,
            detail="Preset name must be 1-64 alphanumeric/dash/underscore/space characters",
        )

    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _safe_filename(payload.name)
    path = PRESETS_DIR / f"{slug}.json"

    data = {"name": payload.name, **payload.config}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {"saved": payload.name, "slug": slug}


@router.delete("/presets/{name}")
def delete_preset(name: str):
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _safe_filename(name)
    path = PRESETS_DIR / f"{slug}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")

    path.unlink()
    return {"deleted": name}
