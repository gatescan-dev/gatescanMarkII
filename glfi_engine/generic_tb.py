import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random
import os
import csv

@cocotb.test()
async def universal_blind_testbench(dut):
    """
    تست‌بنچ جامع و کور برای تولید بردارهای تصادفی و ثبت پاسخ مدار مجهز شده به خطای سخت‌افزاری
    """
    # ۱. شناسایی خودکار پورت‌های کلاک، ریست، ورودی‌های دیتا و پورت‌های کنترلی خطا
    clock_signal = None
    inputs = []
    outputs = []
    
    for port in dut:
        port_name = port._name.lower()
        
        # فیلتر کردن پورت‌های کنترلیِ اختصاصی که خودمان (Instrumentor) اضافه کردیم
        if port_name in ["fi_enable", "fi_target", "fi_value"]:
            continue
            
        # شناسایی کلاک
        if port_name in ["clk", "clock", "ck", "mclk"]:
            clock_signal = port
        # دسته‌بندی بقیه پورت‌ها (اگر نامشخص بود، به عنوان ورودی‌های دیتای خام در نظر می‌گیریم)
        elif port.direction == "input":
            inputs.append(port)
        elif port.direction == "output":
            outputs.append(port)

    # ۲. راه‌اندازی کلاک (اگر مدار ترتیبی باشد)
    if clock_signal is not None:
        cocotb.start_soon(Clock(clock_signal, 10, units="ns").start())

    # ۳. پیکربندی اولیه مدار (مدار سالم - Golden Setup)
    dut.fi_enable.value = 0 # خطا خاموش است
    dut.fi_target.value = 0
    dut.fi_value.value = 0
    
    # گرفتن تعداد کلاک‌سایکل‌ها از لایه مدیریتی (پایتون)
    sim_cycles = int(os.environ.get("SIM_CYCLES", "1000"))
    
    # آماده‌سازی فایل CSV برای ثبت لاگ
    results_file = open('campaign_results.csv', mode='w', newline='')
    csv_writer = csv.writer(results_file)
    
    # ساخت هدر فایل CSV به صورت داینامیک بر اساس خروجی‌های مدار
    header = ["Cycle", "FI_Enable", "FI_Target"] + [out._name for out in outputs]
    csv_writer.writerow(header)

    # ۴. حلقه اصلی شبیه‌سازی (تزریق رندوم دیتا و نمونه‌برداری)
    for cycle in range(sim_cycles):
        # اعمال مقادیر کاملاً تصادفی به تمامی پورت‌های ورودی مدار (به جز کلاک و پورت‌های FI)
        for pin in inputs:
            # pin.value = random.randint(0, (2**len(pin)) - 1)
            # برای سادگی در مدارهای تک‌بیتی:
            try:
                pin.value = random.choice([0, 1])
            except Exception:
                pass # هندل کردن پورت‌های با عرض بیشتر در نسخه‌های توسعه‌یافته‌تر

        # صبر کردن برای لبه بالارونده کلاک (یا یک تاخیر ثابت اگر مدار ترکیبی باشد)
        if clock_signal is not None:
            await RisingEdge(clock_signal)
        else:
            await Timer(10, units="ns")

        # خواندن وضعیت خروجی‌ها
        current_outputs = [str(out.value) for out in outputs]
        
        # ثبت در فایل CSV
        row_data = [cycle, str(dut.fi_enable.value), str(dut.fi_target.value)] + current_outputs
        csv_writer.writerow(row_data)

    results_file.close()
    dut._log.info(f"Blind simulation finished. {sim_cycles} cycles executed.")