# 🧠 GateScan Mark II

**Cognitive Behavioral Engine — Multi-Agent Fault Injection Platform**

> **شماره نسخه:** ۲.۰  
> **موضوع:** آناتومی و فیزیولوژی پلتفرم تزریق خطای مبتنی بر هوش مصنوعی (RAG / LLM Agent-Multi)

🌐 **Live Instance:** [https://faass.viracoai.net](https://faass.viracoai.net)  
📦 **GitHub:** [https://github.com/gatescan-dev/gatescanMarkII](https://github.com/gatescan-dev/gatescanMarkII)

GateScan Mark II represents a leap from **blind statistical testing** (Mark I) to **intelligent behavioral verification**. It uses an **Actor-Critic architecture** with **DeepSeek LLM agents** to understand HDL designs, generate targeted testbenches, and verify them automatically — all before injecting stuck-at faults into your FPGA or ASIC designs.

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [The Four Agents](#-the-four-agents)
- [Quick Start](#-quick-start)
- [Step-by-Step Workflow](#-step-by-step-workflow)
- [API Reference](#-api-reference)
- [CSV Report Format](#-csv-report-format)
- [Tech Stack](#-tech-stack)
- [License](#-license)

---

## 🏗 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER HDL CODE                              │
│                    (.v / .sv / .vhd / .vhdl)                      │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ ① Semantic Analyzer Agent 🔍                                    │
│  (DeepSeek - large context)                                      │
│  "What does this circuit DO?"                                    │
│  Output: Circuit Physiology Document (JSON)                      │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ② Actor Agent (Generator) 🎭                                    │
│  (DeepSeek - code generation)                                    │
│  "Write the testbench with meaningful stimuli"                   │
│  Output: cocotb Python testbench file                            │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ③ Critic Agent (Reviewer) ✅                                    │
│  (DeepSeek - reasoning)                                          │
│  "Review for correctness, score 0-100"                           │
│  Auto-retry if score < 70                                        │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ④ Execution Hub ⚡                                               │
│  Icarus Verilog + Cocotb                                         │
│  Stuck-at fault injection on flattened netlist                   │
│  CSV fault report                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧬 The Four Agents

### 1️⃣ Semantic Analyzer
**Model:** DeepSeek (large context window)  
**Input:** Raw VHDL/Verilog RTL code + extracted topology (JSON netlist)  
**Task:** Discover design intent — determine if the circuit is a DSP filter, MAC unit, FSM, ALU, barrel shifter, memory, etc.

**Output — Circuit Physiology Document:**
```json
{
  "design_type": "barrel_shifter",
  "design_summary": "8-bit barrel shifter with 3-bit select",
  "ports": [
    {"name": "din", "direction": "input", "width": 8, "role": "data", "stimulus_type": "pattern"},
    {"name": "sel", "direction": "input", "width": 3, "role": "control", "stimulus_type": "sequential"},
    {"name": "dout", "direction": "output", "width": 8, "role": "data"}
  ],
  "test_scenarios": [
    {"name": "full_range_shift", "description": "Shift all bits through all positions", "cycles": 64},
    {"name": "boundary_sel", "description": "Test min and max select values", "cycles": 16}
  ],
  "clock_info": {"exists": false},
  "reset_info": {"exists": false},
  "evaluation_metrics": ["output_correctness", "timing"]
}
```

### 2️⃣ Actor Agent (Generator)
**Model:** DeepSeek (code-specialized)  
**Input:** Circuit Physiology Document  
**Task:** Generate a complete, executable cocotb testbench with **meaningful** stimuli:

| Design Type | Generated Stimuli |
|---|---|
| DSP / Filter | Sine waves, impulse responses, step functions |
| ALU / Adder | Boundary values, arithmetic sequences, carry edge cases |
| FSM | State transition sequences, illegal state coverage |
| Barrel Shifter | Exhaustive shift patterns, bit rotation tests |
| Memory | Address sweep, data pattern walking 1's |

### 3️⃣ Critic Agent (Reviewer)
**Model:** DeepSeek (reasoning-focused)  
**Input:** Original HDL + Generated testbench code  
**Task:** QA review checking:
- ✅ Port bit-width compatibility
- ✅ Clock setup correctness
- ✅ Reset handling
- ✅ Stimulus quality for design type
- ✅ Signal width validation
- ✅ Python syntax validity

**Output — Review Report:**
```json
{
  "score": 92,
  "passed": true,
  "port_check": {"status": "pass", "issues": []},
  "clock_check": {"status": "pass", "issues": []},
  "stimulus_check": {"status": "pass", "issues": ["Only 50 cycles for 64 required"]}
}
```

### 4️⃣ Execution Hub
**Infrastructure:** GLFI Engine (Icarus Verilog + Cocotb)  
**Task:** Execute the verified testbench, inject stuck-at-0 / stuck-at-1 faults on every gate in the flattened netlist, and report which faults propagate to outputs.

---

## 🚀 Quick Start

### 1. Visit the Platform
```
https://faass.viracoai.net
```

> 🖥️ **Direct access:** `http://154.91.170.5:8080` (if DNS not yet propagated)

### 2. Step-by-Step Workflow

**Step 1 — Upload Design 📁**
- Drag & drop your `.v` / `.sv` / `.vhd` / `.vhdl` files
- Click "Continue"

**Step 2 — Configuration ⚙️**
- Enter the **top module name** (the actual module in your code, not the filename)
- Select output formats (Verilog netlist, JSON netlist, RTL schematic)
- Enter your **DeepSeek API key** (get one at [platform.deepseek.com](https://platform.deepseek.com))
- Set simulation cycles for fault injection
- Click **Synthesize**, then **Run Mark II**

**Step 3 — Agent Pipeline 🧠**
- Watch the three agents work in real-time:
  - 🔍 **Analyzer** identifies your design type
  - 🎭 **Actor** generates the testbench
  - ✅ **Critic** reviews and scores it
- Auto-retries if score is below 70

**Step 4 — Results 📊**
- View the **Circuit Physiology Document**
- Review the **quality checks** (port, clock, reset, stimulus, width, syntax)
- Download the **generated testbench** code
- Run **Fault Injection** with configurable cycle count
- Download the **CSV fault report**

---

## 📡 API Reference

### Mark II Pipeline
```
POST /api/mark2/run
Body: session_id, top_module, api_key
→ { "task_id": "mark2_xxx", "status": "processing" }

GET /api/mark2/status/{task_id}
→ { "status": "completed", "overall_progress": 100, "result": {...} }
```

### Get Artifacts
```
GET /api/mark2/physiology/{session_id}     → Circuit Physiology JSON
GET /api/mark2/testbench/{session_id}      → Generated Python code
GET /api/mark2/review/{session_id}         → Review report JSON
```

### Synthesis
```
POST /api/synthesis/run
GET /api/synthesis/status/{task_id}
```

### Fault Injection
```
POST /api/glfi/run
GET /api/glfi/status/{task_id}
```

### File Download
```
GET /api/sessions/{session_id}/netlist.v
GET /api/sessions/{session_id}/netlist.json
GET /api/sessions/{session_id}/schematic.svg
GET /api/sessions/{session_id}/schematic.png
GET /api/sessions/{session_id}/campaign_results.csv
```

---

## 📄 CSV Report Format

```
Target_ID,Net_Name,Zone,Fault_Type,Masked_Cycles,Propagated_Cycles,Status
1,_039_,COMB_CLOUD,SA0,3,17,Vulnerable
1,_039_,COMB_CLOUD,SA1,3,17,Vulnerable
```

| Column | Description |
|---|---|
| `Target_ID` | Unique gate identifier |
| `Net_Name` | Output net name of the gate |
| `Zone` | `COMB_CLOUD` (combinational) or `STATE_MEMORY` (sequential) |
| `Fault_Type` | `SA0` (stuck-at-0) or `SA1` (stuck-at-1) |
| `Masked_Cycles` | Cycles where fault did NOT propagate to any output |
| `Propagated_Cycles` | Cycles where fault DID propagate to an output |
| `Status` | `Masked` (100% masked) or `Vulnerable` (some propagation detected) |

---

## 🛠 Tech Stack

| Component | Technology |
|---|---|
| **AI Agents** | DeepSeek (deepseek-chat) |
| **Backend** | Python 3.13 + FastAPI |
| **Synthesis** | Yosys 0.52 + GHDL 5.0 |
| **Simulation** | Icarus Verilog 12 + Cocotb 2.0 |
| **Frontend** | React 18 + Tailwind CSS v4 + Framer Motion |
| **SVG Rendering** | Graphviz + custom beautifier (color legend) |
| **PNG Conversion** | librsvg2 (rsvg-convert) |
| **Auth** | DeepSeek API key (user-provided, per-session) |

---

## 🎨 SVG Color Legend

When you enable the RTL Schematic output, the generated SVG includes a color legend:

| Color | Cell Type |
|---|---|
| 🟢 Green `#22c55e` | AND / ANDNOT |
| 🔵 Blue `#3b82f6` | OR / ORNOT |
| 🔴 Red `#ef4444` | NOT (Inverter) |
| 🟣 Purple `#8b5cf6` | MUX |
| 🟠 Orange `#f59e0b` | DFF (Flip-flop) |
| ⚫ Dark Slate `#1e293b` | I/O Port |

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Maintainers:** [mhsh77](https://github.com/mhsh77) · [aliroshanidino](https://github.com/aliroshanidino)  
**Organization:** [gatescan-dev](https://github.com/gatescan-dev)

---

*"From blind vectors to intelligent verification — Mark II understands your design."*
