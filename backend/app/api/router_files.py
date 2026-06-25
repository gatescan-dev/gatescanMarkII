from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".v", ".json", ".svg", ".csv", ".ys", ".txt", ".png"}

import subprocess
import shutil

@router.get("/{session_id}/{filename}.png")
async def get_session_png(session_id: str, filename: str):
    svg_filename = filename + ".svg"
    svg_path = settings.WORKSPACES_DIR / session_id / svg_filename
    if not svg_path.exists() or not svg_path.is_file():
        raise HTTPException(status_code=404, detail="SVG source not found. Run synthesis with SVG output first.")

    png_path = settings.WORKSPACES_DIR / session_id / (filename + ".png")
    if not png_path.exists():
        try:
            subprocess.run(
                ["rsvg-convert", str(svg_path), "-o", str(png_path)],
                check=True, capture_output=True, timeout=30
            )
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"PNG conversion failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="rsvg-convert not installed")

    return FileResponse(str(png_path), media_type="image/png")

@router.get("/{session_id}/{filename:path}")
async def get_session_file(session_id: str, filename: str):
    # Security: prevent path traversal
    clean_name = Path(filename).name
    if clean_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not Path(clean_name).suffix in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    file_path = settings.WORKSPACES_DIR / session_id / clean_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not Found")

    return FileResponse(str(file_path))
