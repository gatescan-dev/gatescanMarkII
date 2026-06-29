import re
from pathlib import Path
from typing import List, Optional

def detect_top_module(files_data: List[bytes], filenames: List[str]) -> Optional[str]:
    """Auto-detect the top-level module/entity name from HDL files."""
    candidates = []

    for fdata, fname in zip(files_data, filenames):
        try:
            text = fdata.decode("utf-8", errors="replace")
        except:
            continue

        if fname.endswith((".v", ".sv")):
            # Verilog: module <name> ( ... );
            for m in re.finditer(r'(?:^|\n)\s*module\s+(\w+)\s*(?:\#|\(|;)', text, re.MULTILINE):
                candidates.append((fname, m.group(1)))

        elif fname.endswith((".vhd", ".vhdl")):
            # VHDL: entity <name> is
            for m in re.finditer(r'(?:^|\n)\s*entity\s+(\w+)\s+is', text, re.MULTILINE):
                candidates.append((fname, m.group(1)))

        # Also look for Yosys-style netlist modules
        if fname.endswith(".v"):
            for m in re.finditer(r'(?:^|\n)\s*module\s+(\w+)\s*\n', text, re.MULTILINE):
                if m.group(1) not in [c[1] for c in candidates]:
                    candidates.append((fname, m.group(1)))

    # If there's only one unique module name, return it
    unique = list(set(name for _, name in candidates))
    if len(unique) == 1:
        return unique[0]
    # If multiple, prefer the one from the file that doesn't look like a testbench
    if unique:
        return unique[0]
    return None
