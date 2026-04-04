"""
Universal text → JSON converter.
Handles both section-header formats:
  - "STROKES — ALL N DETAIL CURVES" (moto_rider style)
  - "── STROKES ──" (hero/biker style)
"""
import json, re, sys

def convert(txt_path, json_path=None):
    if json_path is None:
        json_path = txt_path.rsplit(".", 1)[0] + ".json"
    
    with open(txt_path) as f:
        lines = f.readlines()
    
    contour, strokes = [], []
    in_contour = in_strokes = False
    
    for line in lines:
        line = line.rstrip()
        
        # Detect contour section (both formats)
        if re.match(r'── CONTOUR', line) or ("idx" in line and "dx" in line and "dy" in line):
            in_contour = True
            continue
        
        # Detect measurements → end contour
        if re.match(r'── MEASURE', line) or (line.startswith("====") and in_contour and len(contour) > 10):
            in_contour = False
            continue
        
        # Detect strokes section (both formats)
        if re.match(r'── STROKES', line) or ("STROKES" in line and "DETAIL" in line):
            in_contour = False
            in_strokes = True
            continue
        
        # Parse contour point
        if in_contour:
            m = re.match(r'\s*(\d+)\s+([+-]?\d+\.\d+)\s+(\d+\.\d+)', line)
            if m:
                contour.append([float(m.group(2)), float(m.group(3))])
        
        # Parse stroke
        if in_strokes:
            sm = re.match(r'\s*stroke\[\s*\d+\]\s*\(\s*\d+\s*pts\):\s*(.*)', line)
            if sm:
                points = re.findall(r'\(([^)]+)\)', sm.group(1))
                strokes.append([[float(x) for x in p.split(',')] for p in points])
    
    data = {
        "contour": contour,
        "strokes": strokes,
        "meta": {
            "contour_points": len(contour),
            "detail_strokes": len(strokes),
            "source": txt_path.split("/")[-1]
        }
    }
    
    with open(json_path, "w") as f:
        json.dump(data, f)
    
    print(f"{txt_path} → {json_path}")
    print(f"  Contour: {len(contour)} pts, Strokes: {len(strokes)}")
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert.py <input.txt> [output.json]")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
