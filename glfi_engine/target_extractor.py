import json
import re
import argparse
from pathlib import Path
from tech_profile import GenericProfile

class WebTargetExtractor:
    """Reads Verilog directly, finds Exact String Blocks, and applies Generic Zoning."""
    
    def __init__(self, input_v: str, output_manifest: str, top_module: str = "top"):
        self.input_v = Path(input_v)
        self.output_manifest = Path(output_manifest)
        self.top_module = top_module

    def get_zone(self, domain: str) -> str:
        """Generic hardware zoning since the web platform accepts any circuit."""
        if domain == "SEQ":
            return "STATE_MEMORY"
        return "COMB_CLOUD"

    def execute(self):
        print(f"[EXTRACTOR] Extracting targets DIRECTLY from Verilog for: {self.top_module}")
        
        if not self.input_v.exists():
            raise FileNotFoundError(f"Verilog netlist not found at {self.input_v}")
            
        with open(self.input_v, 'r') as f:
            content = f.read()

        # شناسایی سلول‌های Yosys با استفاده از Regex
        pattern = re.compile(r'^[ \t]*(\\?\$_[A-Za-z0-9_]+_)\s+([^ \t\n\(]+).*?\((.*?)\);', re.MULTILINE | re.DOTALL)
        matches = pattern.finditer(content)

        targets = []
        target_id = 1
        zone_stats = {"STATE_MEMORY": 0, "COMB_CLOUD": 0}

        for match in matches:
            exact_block = match.group(0)     
            cell_type = match.group(1).strip()       
            inst_name = match.group(2).strip() 
            ports_block = match.group(3)

            # استفاده از پروفایل جنریک برای تشخیص پین خروجی
            cell_info = GenericProfile.get_cell_info(cell_type)
            out_pin = cell_info["out_pin"]
            domain = cell_info["domain"]

            # استخراج دقیق سیمی که به پین Y یا Q متصل شده است
            out_match = re.search(r'\.\s*' + out_pin + r'\s*\(\s*([^)]+?)\s*\)', ports_block)
            if not out_match:
                continue

            # 🌟 رفع باگ نام‌گذاری سیم‌های Escaped در Yosys 🌟
            # اگر نام سیم با بک‌اسلش شروع شود، کاراکتر فاصله (Space) در انتهای آن جزو نام است و نباید Strip شود!
            raw_net = out_match.group(1)
            if raw_net.startswith('\\') and raw_net.endswith(' '):
                out_net = raw_net
            else:
                out_net = raw_net.strip()

            zone = self.get_zone(domain)

            targets.append({
                "id": target_id,
                "cell_type": cell_type,
                "inst_name": inst_name,
                "out_pin": out_pin,
                "out_net": out_net,
                "zone": zone,
                "exact_block": exact_block 
            })

            zone_stats[zone] += 1
            target_id += 1

        # ذخیره در فایل Manifest
        self.output_manifest.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_manifest, 'w') as f:
            json.dump({
                "top_module": self.top_module,
                "total_targets": len(targets),
                "targets": targets
            }, f, indent=4)

        print("==================================================")
        print("🎯 TARGET EXTRACTION COMPLETE (VERILOG NATIVE)")
        print(f"Total Injectable Gates Found: {len(targets)}")
        for z, c in zone_stats.items():
            if c > 0:
                print(f"  ➤ {z:<15}: {c} gates")
        print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_v", required=True, help="Path to flattened Verilog netlist")
    parser.add_argument("--output_manifest", required=True, help="Path to save targets.json")
    parser.add_argument("--top_module", default="top", help="Name of the top module")
    
    args = parser.parse_args()
    agent = WebTargetExtractor(args.input_v, args.output_manifest, args.top_module)
    agent.execute()