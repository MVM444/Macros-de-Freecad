# Libreria de simbolos 2D HVAC (STEP)

Este directorio permite definir simbolos 2D por modelo, como en Electric-CR.

El catalogo HVAC ahora define el archivo 2D por modelo con el campo `Step2DFile`
(en paralelo al `StepFile` 3D), para poder reemplazar modelos sin cambiar codigo.

Estructura:

- `evaporators/`
- `condensers/`

Regla de busqueda para cada equipo:

- Primero: `<Modelo>_2D.step`
- Luego: `<Modelo>_2d.step`
- Luego: `<Modelo>.step`

Ejemplos:

- `evaporators/Pared_12000_2D.step`
- `evaporators/Cassette_60000_2D.step`
- `condensers/MiniSplit_12000_Horizontal_2D.step`
- `condensers/Condenser_36000_Vertical_2D.step`

Si no existe STEP 2D para un modelo, el workbench usa el simbolo 2D generado por codigo.
