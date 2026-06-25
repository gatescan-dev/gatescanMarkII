# glfi_engine/instrumentor.py

import re
import json
import argparse
from pathlib import Path

class WebInstrumentor:
    """Weaves saboteurs purely based on Exact String Block Replacement for Generic Netlists."""
    
    def __init__(self, input_v: str, manifest_json: str, output_v: str, top_module: str = "top"):
        self.input_v = Path(input_v)
        self.targets_manifest = Path(manifest_json)
        self.output_v = Path(output_v)
        self.top_module = top_module

    def execute(self):
        print(f"[INSTRUMENTOR] Starting Bulletproof Verilog Instrumentation for {self.top_module}...")
        
        if not self.targets_manifest.exists():
            raise FileNotFoundError(f"Manifest not found: {self.targets_manifest}")

        with open(self.targets_manifest, 'r') as f:
            manifest = json.load(f)
            targets = manifest.get("targets", [])
            
        with open(self.input_v, 'r') as f:
            content = f.read()

        # پیدا کردن اعلان ماژول و اضافه کردن پورت‌های کنترلی خطا
        module_pattern = re.compile(rf'\bmodule\s+{self.top_module}\s*\((.*?)\)\s*;', re.DOTALL)
        match = module_pattern.search(content)
        
        if not match:
            raise RuntimeError(f"CRITICAL: Module '{self.top_module}' declaration not found!")
            
        original_ports = match.group(1)
        new_ports = original_ports + ", fi_enable, fi_target_id, fi_value"
        content = content.replace(f"({original_ports})", f"({new_ports})", 1)

        # ساخت گذرگاه (Bus) تزریق خطا
        fault_bus_declarations = "\n  // --- FAULT INJECTION BUS ---\n"
        fault_bus_declarations += "  input fi_enable;\n"
        fault_bus_declarations += "  input [31:0] fi_target_id;\n"
        fault_bus_declarations += "  input fi_value;\n"
        fault_bus_declarations += "  // ---------------------------\n"
        
        content = module_pattern.sub(rf"module {self.top_module}({new_ports});\n{fault_bus_declarations}", content, count=1)

        saboteur_logic = "\n  // === SHADOW-HOOK SABOTEURS ===\n"
        successful_weaves = 0

        # حلقه روی تمام اهداف استخراج شده
        for target in targets:
            old_block = target["exact_block"]
            out_pin = target["out_pin"]
            out_net = target["out_net"]
            t_id = target["id"]

            if old_block not in content:
                continue

            # ساخت نام امن برای سیمِ هوک
            safe_net = re.sub(r'[^a-zA-Z0-9_]', '_', out_net)
            hook_net = f"hook_{safe_net}_{t_id}"

            # جایگزینی فقط و فقط روی همان پینی که اکستراکتور پیدا کرده بود
            pin_pattern = re.compile(r'(\.\s*' + out_pin + r'\s*\(\s*)' + re.escape(out_net) + r'(\s*\))')
            new_block = pin_pattern.sub(rf'\g<1>{hook_net}\g<2>', old_block)

            if new_block != old_block:
                content = content.replace(old_block, new_block, 1)
                
                # اضافه کردن منطق MUX برای این گره
                saboteur_logic += f"  wire {hook_net};\n"
                saboteur_logic += f"  assign {out_net} = (fi_enable && fi_target_id == 32'd{t_id}) ? fi_value : {hook_net};\n"
                
                successful_weaves += 1

        saboteur_logic += "  // =============================\n"
        # قرار دادن تمام منطق‌های خرابکار قبل از بسته شدن ماژول
        content = re.sub(r'\bendmodule\b', f"{saboteur_logic}\nendmodule", content)

        # ذخیره فایل نهایی
        self.output_v.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_v, 'w') as f:
            f.write(content)

        print(f"[INSTRUMENTOR] Instrumentation complete! Weaved {successful_weaves}/{len(targets)} explicit hooks.")
        if successful_weaves == 0:
            raise RuntimeError("CRITICAL: Failed to weave ANY hooks! Netlist format mismatch.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_v", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output_v", required=True)
    parser.add_argument("--top_module", default="top")
    
    args = parser.parse_args()
    agent = WebInstrumentor(args.input_v, args.manifest, args.output_v, args.top_module)
    agent.execute()