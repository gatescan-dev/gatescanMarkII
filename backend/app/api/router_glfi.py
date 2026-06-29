import uuid
import threading
import json
import os
import time
from fastapi import APIRouter, Form, HTTPException
from app.core.config import settings
from app.services.glfi_manager import GLFIManager
from app.core.progress import progress

router = APIRouter()

def _run_glfi_task(task_id: str, session_id: str, workspace_path, top_module: str, sim_cycles: int):
    progress.create(task_id)
    progress.set_status(task_id, "processing")
    progress.set_progress(task_id, 0, "Starting fault injection...")

    try:
        progress.set_progress(task_id, 2, "Extracting targets")
        glfi_engine = GLFIManager(workspace_path=workspace_path)

        # Step 1: Target extraction
        target_manifest = workspace_path / "targets.json"
        import subprocess
        subprocess.run([
            "python3", str(settings.ENGINE_DIR / "target_extractor.py"),
            "--input_v", str(workspace_path / "netlist.v"),
            "--output_manifest", str(target_manifest),
            "--top_module", top_module
        ], check=True, capture_output=True, text=True)

        with open(target_manifest) as f:
            targets_data = json.load(f)
        total_targets = targets_data.get("total_targets", 0)
        total_faults = total_targets * 2

        progress.set_progress(task_id, 5, f"Found {total_targets} gates ({total_faults} fault targets)")

        if total_targets == 0:
            progress.set_progress(task_id, 100, "No injectable gates found")
            result = {
                "status": "success",
                "message": f"No injectable gates found in design.",
                "data": {
                    "results_csv": "",
                    "total_faults": 0,
                    "vulnerable": 0,
                    "masked": 0
                }
            }
            progress.set_status(task_id, "completed", result=result)
            return

        # Step 2: Instrumentation
        progress.set_progress(task_id, 7, "Instrumenting netlist")
        subprocess.run([
            "python3", str(settings.ENGINE_DIR / "instrumentor.py"),
            "--input_v", str(workspace_path / "netlist.v"),
            "--manifest", str(target_manifest),
            "--output_v", str(workspace_path / "instrumented.v"),
            "--top_module", top_module
        ], check=True, capture_output=True, text=True)

        # Step 3: Run simulation
        progress.set_progress(task_id, 10, "Starting simulation")

        cocotb_config = "/opt/openfiaas/venv/bin/cocotb-config"
        progress_file = str(workspace_path / "glfi_progress.json")

        makefile_path = workspace_path / "Makefile"
        with open(makefile_path, "w") as f:
            f.write("SIM ?= icarus\n")
            f.write("TOPLEVEL_LANG ?= verilog\n")
            f.write("YOSYS_DATDIR = $(shell yosys-config --datdir)\n")
            f.write("VERILOG_SOURCES += $(YOSYS_DATDIR)/simcells.v\n")
            f.write(f"VERILOG_SOURCES += {workspace_path / 'instrumented.v'}\n")
            f.write(f"TOPLEVEL = {top_module}\n")
            f.write(f"COCOTB_MAKEFILES := $(shell {cocotb_config} --makefiles)\n")
            f.write("COCOTB_TEST_MODULES = cocotb_orchestrator\n")
            f.write("include $(COCOTB_MAKEFILES)/Makefile.sim\n")

        env_vars = os.environ.copy()
        venv_bin = "/opt/openfiaas/venv/bin"
        env_vars["PATH"] = f"{venv_bin}:" + env_vars.get("PATH", "")
        env_vars["PYTHONPATH"] = str(settings.ENGINE_DIR) + ":" + env_vars.get("PYTHONPATH", "")
        env_vars["TOP_MODULE"] = top_module
        env_vars["SIM_CYCLES"] = str(sim_cycles)
        env_vars["MANIFEST_PATH"] = str(target_manifest)
        env_vars["CSV_RESULTS_PATH"] = str(workspace_path / "campaign_results.csv")
        env_vars["PROGRESS_FILE"] = progress_file

        # Run make in background thread that we can monitor
        proc = subprocess.Popen(
            ["make"],
            cwd=str(workspace_path),
            env=env_vars,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Poll for progress updates while make runs
        while proc.poll() is None:
            time.sleep(1)
            try:
                with open(progress_file) as pf:
                    pdata = json.load(pf)
                    progress.set_progress(task_id, pdata.get("pct", 50),
                        f"{pdata.get('stage','')}: {pdata.get('detail','')}")
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Simulation failed (exit code {proc.returncode})")

        progress.set_progress(task_id, 100, "Campaign complete")

        # Count results
        import csv
        vulnerable = 0
        masked = 0
        try:
            with open(workspace_path / "campaign_results.csv") as cf:
                reader = csv.DictReader(cf)
                for row in reader:
                    if row.get("Status") == "Vulnerable":
                        vulnerable += 1
                    else:
                        masked += 1
        except Exception:
            pass

        result = {
            "status": "success",
            "message": f"Fault campaign completed for {sim_cycles} cycles.",
            "data": {
                "results_csv": str(workspace_path / "campaign_results.csv"),
                "total_faults": total_faults,
                "vulnerable": vulnerable,
                "masked": masked
            }
        }
        progress.set_status(task_id, "completed", result=result)

    except Exception as e:
        progress.set_status(task_id, "failed", error=str(e))

@router.post("/run")
async def run_fault_campaign(
    session_id: str = Form(...),
    top_module: str = Form(...),
    sim_cycles: int = Form(1000)
):
    workspace_path = settings.WORKSPACES_DIR / session_id
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    task_id = f"glfi_{session_id}"
    thread = threading.Thread(
        target=_run_glfi_task,
        args=(task_id, session_id, workspace_path, top_module, sim_cycles),
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
