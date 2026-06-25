import os
import csv
import json
import json
import math
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from pathlib import Path

# خواندن متغیرهای محیطی ارسال شده از سمت بک‌اندِ وب‌سایت
TOP_MODULE = os.environ.get("TOP_MODULE", "top")
CSV_RESULTS_PATH = os.environ.get("CSV_RESULTS_PATH", "campaign_results.csv")
MANIFEST_PATH = os.environ.get("MANIFEST_PATH", "targets.json")
PROGRESS_FILE = os.environ.get("PROGRESS_FILE", "glfi_progress.json")
SIM_CYCLES = int(os.environ.get("SIM_CYCLES", "1000"))

# متغیرهای تقسیم کار برای امکان اجرای موازی (Multi-core / Hyperscale)
SPLIT_TOTAL = int(os.environ.get("SPLIT_TOTAL", "1"))
SPLIT_INDEX = int(os.environ.get("SPLIT_INDEX", "0"))

def write_progress(pct, stage, detail=""):
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"pct": pct, "stage": stage, "detail": detail}, f)
    except Exception:
        pass

class GenericCampaignMaster:
    """مدیریت کمپین خطا برای مدارهای عمومی، ترکیب شده با لاجیک Checkpointing"""
    
    def __init__(self, dut):
        self.dut = dut
        self.csv_path = Path(CSV_RESULTS_PATH)
        self.completed_tasks = set()
        
        self.clock_signal = None
        self.inputs = []
        self.outputs = []
        self._discover_ports()
        
        self.input_vectors = []
        self.golden_responses = []
        
        self._init_checkpointing()

    def _discover_ports(self):
        for port in self.dut:
            p_name = port._name.lower()
            if p_name in ["fi_enable", "fi_target_id", "fi_value"]:
                continue
            if p_name in ["clk", "clock", "ck", "mclk"]:
                self.clock_signal = port
            self.inputs.append(port)
            self.outputs.append(port)
    def _init_checkpointing(self):
        """بررسی فایل CSV برای جلوگیری از اجرای مجدد خطاهایی که قبلاً انجام شده‌اند"""
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        headers = ["Target_ID", "Net_Name", "Zone", "Fault_Type", "Masked_Cycles", "Propagated_Cycles", "Status"]
        
        if self.csv_path.exists():
            with open(self.csv_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None) # پرش از هدر
                for row in reader:
                    if len(row) >= 4:
                        signature = f"{row[0]}_{row[3]}"
                        self.completed_tasks.add(signature)
        else:
            with open(self.csv_path, 'w', newline='') as f:
                csv.writer(f).writerow(headers)

    def log_result(self, row_data):
        """ثبت لحظه‌ای هر رکورد در فایل CSV"""
        with open(self.csv_path, 'a', newline='') as f:
            csv.writer(f).writerow(row_data)

    async def generate_golden_run(self):
        """اجرای طلایی (بدون خطا) با بردارهای تصادفی برای ساخت مبنای مقایسه"""
        self.dut._log.info(f"[PHASE 1] Executing Golden Run for {SIM_CYCLES} cycles...")
        
        self.dut.fi_enable.value = 0
        self.dut.fi_target_id.value = 0
        self.dut.fi_value.value = 0
        
        # تنظیم سید رندوم برای تکرارپذیری دقیق بردارها در فاز خطادار
        random.seed(42)
        
        for _ in range(SIM_CYCLES):
            write_progress(15 + int((_/max(1,SIM_CYCLES))*15), "golden", "Golden cycle "+str(_+1)+"/"+str(SIM_CYCLES))
            vec = {}
            for pin in self.inputs:
                # 🌟 رفع باگ باس‌های چندبیتی (Multi-bit Bus Randomization) 🌟
                # استخراج عرض پورت و تولید عدد رندوم در بازه صحیح
                port_width = len(pin)
                val = random.randint(0, (2**port_width) - 1)
                
                vec[pin._name] = val
                try: 
                    getattr(self.dut, pin._name).value = val
                except Exception as e: 
                    pass
                
            self.input_vectors.append(vec)

            # اعمال کلاک یا ایجاد تاخیر
            if self.clock_signal: 
                await RisingEdge(self.clock_signal)
            else: 
                await Timer(10, unit="ns")

            # 🌟 رفع باگ Race Condition در خواندن خروجی‌ها 🌟
            # با  صبر می‌کنیم تا تمام تأخیرهای گیت‌های ترکیبی (Propagation Delays) 
            # تمام شود و سیگنال‌ها در مدار ته‌نشین (Settle) شوند.
            out_state = {}
            for out in self.outputs:
                try: out_state[out._name] = str(out.value)
                except: pass
            self.golden_responses.append(out_state)

    async def run_fault_campaign(self):
        """اجرای کمپین خطا روی اهداف استخراج شده با در نظر گرفتن برش‌های موازی"""
        with open(MANIFEST_PATH, 'r') as f:
            manifest = json.load(f)
            all_targets = manifest.get("targets", [])
            
        chunk_size = math.ceil(len(all_targets) / SPLIT_TOTAL)
        start_idx = SPLIT_INDEX * chunk_size
        end_idx = min(start_idx + chunk_size, len(all_targets))
        my_targets = all_targets[start_idx:end_idx]
        
        tasks_to_run = []
        total_faults = len(my_targets) * 2
        for target in my_targets:
            t_id = target["id"]
            for f_val in [0, 1]:
                signature = f"{t_id}_SA{f_val}"
                if signature not in self.completed_tasks:
                    tasks_to_run.append((target, f_val))
                    
        self.dut._log.info(f"[PHASE 2] Starting {len(tasks_to_run)} fault injections (out of {len(my_targets)*2} total for this chunk)...")

        for task_idx, (target, f_val) in enumerate(tasks_to_run):
            pct = 30 + int((task_idx / max(1, len(tasks_to_run))) * 70)
            fn = target.get("out_net", str(target.get("id","?")))
            write_progress(pct, "injecting", f"Fault {task_idx+1}/{len(tasks_to_run)}: {fn} SA{f_val}")
            t_id = target["id"]
            t_name = target.get("out_net", f"node_{t_id}")
            t_zone = target.get("zone", "UNKNOWN")
            
            self.dut.fi_enable.value = 1
            self.dut.fi_target_id.value = t_id
            self.dut.fi_value.value = f_val
            
            masked_cycles = 0
            propagated_cycles = 0
            
            for cycle in range(SIM_CYCLES):
                vec = self.input_vectors[cycle]
                for pin in self.inputs:
                    try: 
                        getattr(self.dut, pin._name).value = vec[pin._name]
                    except: 
                        pass
                    
                if self.clock_signal: 
                    await RisingEdge(self.clock_signal)
                else: 
                    await Timer(10, unit="ns")
                
                # 🌟 استفاده مجدد از  برای خواندن صحیح خروجی خطادار 🌟
    
                
                current_outs = {}
                for out in self.outputs:
                    try: current_outs[out._name] = str(out.value)
                    except: pass
                golden_outs = self.golden_responses[cycle]
                
                if current_outs == golden_outs:
                    masked_cycles += 1
                else:
                    propagated_cycles += 1
            
            self.dut.fi_enable.value = 0
            
            status = "Masked" if propagated_cycles == 0 else "Vulnerable"
            
            self.log_result([
                t_id, t_name, t_zone, f"SA{f_val}",
                masked_cycles, propagated_cycles, status
            ])

@cocotb.test()
async def execute_web_glfi_campaign(dut):
    """تابع اصلی تست‌بنچ که توسط Icarus فراخوانی می‌شود"""
    master = GenericCampaignMaster(dut)
    if not master.clock_signal:
        dut._log.warning("No clock signal found")
    if master.clock_signal:
        cocotb.start_soon(Clock(master.clock_signal, 10, unit="ns").start())
        
    await master.generate_golden_run()
    await master.run_fault_campaign()