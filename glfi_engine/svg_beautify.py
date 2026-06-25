#!/usr/bin/env python3
"""Beautify Yosys SVG schematics with cell-type colors and legend."""
import sys, re
from xml.etree import ElementTree as ET
from copy import deepcopy

COLORS = {
    "AND":    {"fill": "#22c55e", "stroke": "#166534", "text": "#ffffff", "label": "AND / ANDNOT"},
    "OR":     {"fill": "#3b82f6", "stroke": "#1e40af", "text": "#ffffff", "label": "OR / ORNOT"},
    "XOR":    {"fill": "#a855f7", "stroke": "#6b21a8", "text": "#ffffff", "label": "XOR / XNOR"},
    "NAND":   {"fill": "#10b981", "stroke": "#065f46", "text": "#ffffff", "label": "NAND"},
    "NOR":    {"fill": "#6366f1", "stroke": "#3730a3", "text": "#ffffff", "label": "NOR"},
    "XNOR":   {"fill": "#d946ef", "stroke": "#86198f", "text": "#ffffff", "label": "XNOR"},
    "NOT":    {"fill": "#ef4444", "stroke": "#991b1b", "text": "#ffffff", "label": "NOT (Inverter)"},
    "MUX":    {"fill": "#8b5cf6", "stroke": "#5b21b6", "text": "#ffffff", "label": "MUX"},
    "DFF":    {"fill": "#f59e0b", "stroke": "#92400e", "text": "#000000", "label": "DFF (Flip-flop)"},
    "PORT":   {"fill": "#1e293b", "stroke": "#64748b", "text": "#94a3b8", "label": "I/O Port"},
}



def classify(texts):
    full = " ".join(texts).upper()
    for key in ["DFF", "MUX", "ANDNOT", "ORNOT", "AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT"]:
        if key in full: return key
    return "PORT" if any("$" not in t and "\\" not in t for t in texts if t.strip()) else None

def add_legend(root, width_pt, height_pt):
    NS = "http://www.w3.org/2000/svg"
    """Append a color legend at the bottom of the SVG."""
    
    legend_y = height_pt + 15
    legend_height = 85
    box_w = 140
    cols = 3
    gap = 10
    leg_start_x = 10
    leg_w = cols * box_w + (cols - 1) * gap + 20
    total_w = max(width_pt + 8, leg_w + 20)
    total_h = height_pt + legend_height + 25

    # Update viewBox
    root.set("width", f"{total_w}pt")
    root.set("height", f"{total_h}pt")
    vb = root.get("viewBox", "")
    parts = vb.split()
    if len(parts) == 4:
        root.set("viewBox", f"{parts[0]} {parts[1]} {max(float(parts[2]), total_w)} {total_h}")

    # Background for legend
    bg = ET.SubElement(root, "rect")
    bg.set("x", str(leg_start_x))
    bg.set("y", str(legend_y - 5))
    bg.set("width", str(leg_w))
    bg.set("height", str(legend_height))
    bg.set("fill", "#1e293b")
    bg.set("rx", "6")
    bg.set("style", "fill:#1e293b;stroke:#334155;stroke-width:1.5")

    # Legend title
    lt = ET.SubElement(root, "text")
    lt.set("x", str(leg_start_x + 10))
    lt.set("y", str(legend_y + 15))
    lt.set("fill", "#94a3b8")
    lt.set("font-family", "sans-serif")
    lt.set("font-size", "13")
    lt.set("font-weight", "bold")
    lt.text = "Legend"

    # Legend items
    items = [
        ("AND", COLORS["AND"]),
        ("OR", COLORS["OR"]),
        ("NOT", COLORS["NOT"]),
        ("MUX", COLORS["MUX"]),
        ("DFF", COLORS["DFF"]),
        ("PORT", COLORS["PORT"]),
    ]

    for i, (key, c) in enumerate(items):
        col = i % cols
        row = i // cols
        x = leg_start_x + 10 + col * box_w
        y = legend_y + 30 + row * 28

        # Color box
        rect = ET.SubElement(root, "rect")
        rect.set("x", str(x))
        rect.set("y", str(y))
        rect.set("width", "14")
        rect.set("height", "14")
        rect.set("rx", "3")
        rect.set("style", f"fill:{c['fill']};stroke:{c['stroke']};stroke-width:1.5")

        # Label
        lbl = ET.SubElement(root, "text")
        lbl.set("x", str(x + 20))
        lbl.set("y", str(y + 12))
        lbl.set("fill", "#cbd5e1")
        lbl.set("font-family", "sans-serif")
        lbl.set("font-size", "11")
        lbl.text = c["label"]

def beautify(inpath, outpath):
    tree = ET.parse(inpath)
    root = tree.getroot()

    # Get original dimensions
    width_pt = float(root.get("width", "400pt").replace("pt", ""))
    height_pt = float(root.get("height", "200pt").replace("pt", ""))

    NS = "http://www.w3.org/2000/svg"
    # Style cell and port nodes
    for g in root.findall(f".//{{{NS}}}g"):
        gid = g.get("id", "")
        if "node" not in gid:
            continue
        texts = [t.text or "" for t in g.findall(f"{{{NS}}}text")]
        cell_type = classify(texts)
        if cell_type == "PORT":
            for poly in g.findall(f"{{{NS}}}polygon"):
                poly.set("style", "fill:#1e293b;stroke:#64748b;stroke-width:1.5")
        elif cell_type:
            colors = COLORS.get(cell_type, COLORS["AND"])
            for poly in g.findall(f"{{{NS}}}polygon"):
                poly.set("style", f"fill:{colors['fill']};stroke:{colors['stroke']};stroke-width:2")
            for tel in g.findall(f"{{{NS}}}text"):
                tel.set("style", f"fill:{colors['text']};font-family:monospace;font-size:12")

    # Style title
    for tel in root.findall(f".//{{{NS}}}text"):
        if tel.text and tel.text.strip() == "top":
            tel.set("style", "fill:#94a3b8;font-family:sans-serif;font-size:18;font-weight:bold")

    # Add legend
    add_legend(root, width_pt, height_pt)

    tree.write(outpath, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: svg_beautify.py <input.svg> <output.svg>")
        sys.exit(1)
    beautify(sys.argv[1], sys.argv[2])
