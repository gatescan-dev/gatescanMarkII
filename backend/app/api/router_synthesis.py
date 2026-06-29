import uuid
import threading
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List
from pathlib import Path

from app.core.config import settings
from app.core.progress import progress
from app.services.yosys_manager import YosysManager

router = APIRouter()

def _run_synth_task(task_id: str, files_data: list, filenames: list, top_module: str, outputs: list):
    progress.create(task_id)
    progress.set_status(task_id, "processing")
    progress.set_progress(task_id, 0, "Initializing...")

    try:
        session_id = task_id.replace("task_", "session_")
        workspace_path = settings.WORKSPACES_DIR / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        progress.set_progress(task_id, 2, "Saving uploaded files")
        saved_files = []
        for fdata, fname in zip(files_data, filenames):
            file_path = workspace_path / fname
            with open(file_path, "wb") as buf:
                buf.write(fdata)
            saved_files.append(file_path)

        progress.set_progress(task_id, 5, "Files saved, starting engine")

        engine = YosysManager(workspace_path=workspace_path)
        generated = engine.run_synthesis(
            rtl_files=saved_files,
            top_module=top_module,
            requested_outputs=outputs,
            task_id=task_id
        )

        result = {
            "status": "success",
            "session_id": session_id,
            "top_module": top_module,
            "results": generated
        }
        progress.set_status(task_id, "completed", result=result)

    except Exception as e:
        progress.set_status(task_id, "failed", error=str(e))

from app.services.top_detector import detect_top_module

@router.post("/detect-top")
async def detect_top(files: List[UploadFile] = File(...)):
    files_data = [await f.read() for f in files]
    filenames = [f.filename for f in files]
    name = detect_top_module(files_data, filenames)
    return {"top_module": name}

@router.post("/run")
async def run_synthesis(
    files: List[UploadFile] = File(...),
    top_module: str = Form(...),
    outputs: str = Form("verilog,json,svg")
):
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    files_data = [await f.read() for f in files]
    filenames = [f.filename for f in files]
    requested = [fmt.strip().lower() for fmt in outputs.split(",")]

    thread = threading.Thread(
        target=_run_synth_task,
        args=(task_id, files_data, filenames, top_module, requested),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "processing"}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    state = progress.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return state
