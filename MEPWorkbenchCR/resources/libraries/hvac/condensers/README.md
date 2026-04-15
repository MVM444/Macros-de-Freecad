# HVAC Condenser STEP Library

This folder stores STEP models for HVAC outdoor condenser units.

Units:
- millimeters (mm)

Origin convention:
- centered in XY
- base at Z = 0

Folder layout:
- `horizontal/`: mini-split side discharge models (12000 to 24000 BTU/h)
- `vertical/`: top discharge models (36000 BTU/h and above)

Expected file names used by `hvac_condensing.py`:
- `Condenser_12000_Horizontal.step`
- `Condenser_18000_Horizontal.step`
- `Condenser_24000_Horizontal.step`
- `Condenser_36000_Vertical.step`
- `Condenser_48000_Vertical.step`
- `Condenser_60000_Vertical.step`

Generator script:
- `_generate_step_catalog.py`
