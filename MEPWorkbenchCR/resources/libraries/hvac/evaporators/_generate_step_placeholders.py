import os
import FreeCAD as App
import Part

OUT_DIR = r"c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\MEPWorkbenchCR\resources\libraries\hvac\evaporators"
os.makedirs(OUT_DIR, exist_ok=True)

# name, (lx, ly, lz) in mm
MODELS = [
    ("placeholder_cube_500.step", (500.0, 500.0, 500.0)),
    ("placeholder_square_plate_1000x1000x30.step", (1000.0, 1000.0, 30.0)),
    ("placeholder_wall_prism_900x260x220.step", (900.0, 260.0, 220.0)),
    ("placeholder_duct_prism_1200x360x320.step", (1200.0, 360.0, 320.0)),
]

for filename, dims in MODELS:
    lx, ly, lz = dims
    doc = App.newDocument("StepGen")
    obj = doc.addObject("Part::Feature", "Body")
    shape = Part.makeBox(float(lx), float(ly), float(lz))
    # Origin convention for insertion: centered in XY, floor on Z=0
    shape.translate(App.Vector(-float(lx) / 2.0, -float(ly) / 2.0, 0.0))
    obj.Shape = shape
    out_path = os.path.join(OUT_DIR, filename)
    Part.export([obj], out_path)
    App.closeDocument(doc.Name)
    print("Generated:", out_path)
