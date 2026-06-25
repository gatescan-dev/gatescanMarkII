import os
import subprocess
from pathlib import Path
from typing import Dict
from app.core.config import settings

class GLFIManager:
    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.engine_path = settings.ENGINE_DIR

    def execute_fault_campaign(self, top_module: str, sim_cycles: int) -> Dict[str, str]:
        flat_netlist = self.workspace / "netlist.v"
        json_netlist = self.workspace / "netlist.json"
        target_manifest = self.workspace / "targets.json"
        instrumented_netlist = self.workspace / "instrumented.v"
        results_csv = self.workspace / "campaign_results.csv"

        if not flat_netlist.exists() or not json_netlist.exists():
            raise FileNotFoundError("Synthesized netlists (.v or .json) are missing in the workspace.")

        subprocess.run([
            "python3", str(self.engine_path / "target_extractor.py"),
            "--input_v", str(flat_netlist),
            "--output_manifest", str(target_manifest),
            "--top_module", top_module
        ], check=True)

        subprocess.run([
            "python3", str(self.engine_path / "instrumentor.py"),
            "--input_v", str(flat_netlist),
            "--manifest", str(target_manifest),
            "--output_v", str(instrumented_netlist),
            "--top_module", top_module
        ], check=True)

        cocotb_config = "/opt/openfiaas/venv/bin/cocotb-config"

        makefile_path = self.workspace / "Makefile"
        with open(makefile_path, "w") as f:
            f.write("SIM ?= icarus\n")
            f.write("TOPLEVEL_LANG ?= verilog\n")
            f.write("YOSYS_DATDIR = $(shell yosys-config --datdir)\n")
            f.write("VERILOG_SOURCES += $(YOSYS_DATDIR)/simcells.v\n")
            f.write(f"VERILOG_SOURCES += {instrumented_netlist.absolute()}\n")
            f.write(f"TOPLEVEL = {top_module}\n")
            f.write(f"COCOTB_MAKEFILES := $(shell {cocotb_config} --makefiles)\n")
            f.write("COCOTB_TEST_MODULES = cocotb_orchestrator\n")
            f.write("include $(COCOTB_MAKEFILES)/Makefile.sim\n")

        env_vars = os.environ.copy()
        venv_bin = "/opt/openfiaas/venv/bin"
        env_vars["PATH"] = f"{venv_bin}:" + env_vars.get("PATH", "")
        env_vars["PYTHONPATH"] = str(self.engine_path) + ":" + env_vars.get("PYTHONPATH", "")
        env_vars["TOP_MODULE"] = top_module
        env_vars["SIM_CYCLES"] = str(sim_cycles)
        env_vars["MANIFEST_PATH"] = str(target_manifest)
        env_vars["CSV_RESULTS_PATH"] = str(results_csv)

        try:
            subprocess.run(["make"], cwd=str(self.workspace), env=env_vars, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Cocotb Simulation Failed: {e}")

        return {"results_csv": str(results_csv)}
