import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Optional

class YosysManager:
    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.yosys_exec = "yosys"
        self.ghdl_exec = "ghdl"

    def _preprocess_vhdl(self, rtl_files: List[Path], top_module: str, task_id: str = None) -> Path:
        from app.core.progress import progress
        vhdl_files = [f for f in rtl_files if str(f).endswith((".vhd", ".vhdl"))]
        if not vhdl_files:
            return None
        synth_verilog = self.workspace / "ghdl_synth.v"
        for i, vhdl_file in enumerate(vhdl_files):
            pct = 10 + int((i / len(vhdl_files)) * 15)
            if task_id: progress.set_progress(task_id, pct, f"GHDL analyze: {vhdl_file.name}")
            result = subprocess.run([self.ghdl_exec, "-a", str(vhdl_file)], cwd=str(self.workspace), capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"GHDL Analysis Failed for {vhdl_file.name}:\n{result.stderr}")
        if task_id: progress.set_progress(task_id, 28, "GHDL synth to Verilog")
        result = subprocess.run([self.ghdl_exec, "--synth", "--out=verilog", top_module], cwd=str(self.workspace), capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GHDL Synthesis Failed:\n{result.stderr}")
        with open(synth_verilog, "w") as f: f.write(result.stdout)
        if task_id: progress.set_progress(task_id, 35, "VHDL preprocessed OK")
        return synth_verilog

    def _generate_ys_script(self, rtl_files: List[Path], top_module: str, outputs: List[str]) -> Path:
        script_path = self.workspace / "synth.ys"
        with open(script_path, "w") as f:
            for rtl in rtl_files:
                rtl_str = str(rtl)
                if rtl_str.endswith(".v") or rtl_str.endswith(".sv"):
                    f.write(f"read_verilog {rtl_str}\n")
            ghdl_v = self.workspace / "ghdl_synth.v"
            if ghdl_v.exists():
                f.write(f"read_verilog {ghdl_v}\n")
            f.write(f"hierarchy -check -top {top_module}\n")
            f.write("proc\n")
            f.write("opt\n")
            if "svg" in outputs:
                f.write(f"show -format svg -colors 2 -prefix {self.workspace / 'schematic'}\n")
            f.write(f"synth -top {top_module} -flatten\n")
            if "json" in outputs:
                f.write(f"write_json {self.workspace / 'netlist.json'}\n")
            if "verilog" in outputs:
                f.write(f"write_verilog -noattr -noexpr {self.workspace / 'netlist.v'}\n")
        return script_path

    def run_synthesis(self, rtl_files: List[Path], top_module: str, requested_outputs: List[str], task_id: str = None) -> Dict[str, str]:
        from app.core.progress import progress
        self._preprocess_vhdl(rtl_files, top_module, task_id)
        if task_id: progress.set_progress(task_id, 40, "Starting Yosys")
        script_path = self._generate_ys_script(rtl_files, top_module, requested_outputs)
        proc = subprocess.Popen([self.yosys_exec, "-s", str(script_path)], cwd=str(self.workspace), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        yosys_start, yosys_end = 40, 95
        line_count = 0
        for line in proc.stdout:
            line_count += 1
            stripped = line.strip()
            if not stripped: continue
            if stripped.startswith("-- Running command"):
                cmd_name = stripped.split("'")[1] if "'" in stripped else stripped
                if task_id: progress.set_progress(task_id, yosys_start + int((line_count / 200) * (yosys_end - yosys_start)), f"Yosys: {cmd_name}")
            elif "Executing" in stripped and "pass" in stripped:
                if task_id:
                    pct = yosys_start + int((line_count / 200) * (yosys_end - yosys_start))
                    progress.set_progress(task_id, pct, f"Yosys: {stripped}")
                    progress.next_yosys_pass(task_id, stripped)
            elif line_count % 10 == 0 and task_id:
                progress.set_progress(task_id, yosys_start + int((line_count / 200) * (yosys_end - yosys_start)), "Yosys processing...")
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Yosys Compilation Failed (exit code {proc.returncode}). Check server logs for details.")
        output_paths = {}
        if "verilog" in requested_outputs: output_paths["verilog"] = str(self.workspace / "netlist.v")
        if "json" in requested_outputs: output_paths["json"] = str(self.workspace / "netlist.json")
        if "svg" in requested_outputs:
            svg_path = self.workspace / "schematic.svg"
            if svg_path.exists():
                try:
                    import subprocess as _sp
                    _sp.run(["/opt/openfiaas/venv/bin/python3", "/opt/openfiaas/glfi_engine/svg_beautify.py", str(svg_path), str(svg_path)], capture_output=True, timeout=15)
                except Exception:
                    pass
                output_paths["svg"] = str(svg_path)
        if task_id: progress.set_progress(task_id, 100, "Complete")
        return output_paths
