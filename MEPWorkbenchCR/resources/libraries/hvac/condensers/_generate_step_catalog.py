import os

import FreeCAD as App
import Part


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
OUT_HORIZONTAL = os.path.join(SCRIPT_DIR, "horizontal")
OUT_VERTICAL = os.path.join(SCRIPT_DIR, "vertical")
os.makedirs(OUT_HORIZONTAL, exist_ok=True)
os.makedirs(OUT_VERTICAL, exist_ok=True)

# filename, (size_x, size_y, size_z), discharge_type
MODELS = [
    ("Condenser_12000_Horizontal.step", (820.0, 320.0, 600.0), "Horizontal"),
    ("Condenser_18000_Horizontal.step", (860.0, 340.0, 620.0), "Horizontal"),
    ("Condenser_24000_Horizontal.step", (900.0, 360.0, 680.0), "Horizontal"),
    ("Condenser_36000_Vertical.step", (900.0, 900.0, 920.0), "Vertical"),
    ("Condenser_48000_Vertical.step", (980.0, 980.0, 980.0), "Vertical"),
    ("Condenser_60000_Vertical.step", (1080.0, 1080.0, 1100.0), "Vertical"),
]


def build_shape(size_xyz, discharge):
    sx, sy, sz = size_xyz
    body = Part.makeBox(float(sx), float(sy), float(sz))
    body.translate(App.Vector(-float(sx) * 0.5, -float(sy) * 0.5, 0.0))
    parts = [body]

    # Simple top fan cue for vertical discharge units.
    if str(discharge or "").strip().lower() == "vertical":
        radius = max(100.0, min(float(sx), float(sy)) * 0.28)
        fan_h = max(10.0, float(sz) * 0.05)
        fan = Part.makeCylinder(radius, fan_h, App.Vector(0.0, 0.0, float(sz) - fan_h), App.Vector(0, 0, 1))
        parts.append(fan)

    if len(parts) == 1:
        return parts[0]
    return Part.Compound(parts)


for filename, size_xyz, discharge in MODELS:
    out_dir = OUT_VERTICAL if discharge == "Vertical" else OUT_HORIZONTAL
    out_path = os.path.join(out_dir, filename)

    doc = App.newDocument("CondenserStepGen")
    obj = doc.addObject("Part::Feature", "Body")
    obj.Shape = build_shape(size_xyz, discharge)
    Part.export([obj], out_path)
    App.closeDocument(doc.Name)
    print("Generated:", out_path)
