import os
import FreeCAD as App
import Part

OUT_DIR = r"c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\MEPWorkbenchCR\resources\libraries\hvac\evaporators"
os.makedirs(OUT_DIR, exist_ok=True)

MODELS = {
    "Pared_9000.step": (760.0, 230.0, 220.0),
    "Pared_12000.step": (900.0, 260.0, 220.0),
    "Pared_18000.step": (1040.0, 280.0, 240.0),
    "Cassette_24000.step": (600.0, 600.0, 320.0),
    "Cassette_36000.step": (840.0, 840.0, 350.0),
    "Ducto_36000.step": (1200.0, 360.0, 320.0),
    "Ducto_60000.step": (1600.0, 450.0, 380.0),
}

for filename, dims in MODELS.items():
    lx, ly, lz = dims
    doc = App.newDocument("StepCat")
    obj = doc.addObject("Part::Feature", "Body")
    shape = Part.makeBox(float(lx), float(ly), float(lz))
    shape.translate(App.Vector(-float(lx) / 2.0, -float(ly) / 2.0, 0.0))
    obj.Shape = shape
    out_path = os.path.join(OUT_DIR, filename)
    Part.export([obj], out_path)
    App.closeDocument(doc.Name)
    print("Generated:", out_path)
