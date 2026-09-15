# Memoria FreeCAD - ElectricCR A1 fisico/documental

Fecha: 2026-09-03
FreeCAD: 1.1.3 revision 20260725
Proyecto: ElectricCR

## Diagnostico

La separacion A1 no estaba implementada aunque aparecia como direccion de
diseno. `TomaUnoProxy._build_shape()` incorporaba `symbol2D` y `model3D` en un
unico `Part.makeCompound`; por tanto la Shape seguia siendo
`LegacyCompound`.

## Patron validado

La identidad colocada continua siendo el `App::Link`. Un master A1 separado
contiene solo la Shape fisica 3D. PLAN se materializa como un `Part::Feature`
`DocumentationOnly`, sin `ElementUID`, con rol `PLAN` y `Owner` hacia la
identidad. La instancia conserva `ElementUID`, `Space`, `Host`, Placement,
altura y su enlace al master.

Se eligio el auxiliar PLAN controlado porque reemplazar el ViewProvider nativo
del Link es fragil y una escena Coin del ViewProvider no es una fuente
documental semantica para DXF. La escala y visibilidad PLAN no alteran la Shape
fisica.

Los masters `PhysicalDocumentationA1` usan sufijo `_A1Physical` y nunca se
mezclan con masters `LegacyCompound`. El valor legacy continua como default
para compatibilidad; la activacion A1 es explicita.

## Prueba MCP

`ElectricCR/tests/freecad_electromechanical_outlet_switch_a1_smoke.py` creo en
un documento temporal exactamente un `Tomacorriente_120V` y un
`Apagador_Simple`. Ambos aprobaron:

- Shape/Volume/BoundBox/Solids fisicos;
- PLAN independiente en Z=0, sin volumen ni solidos;
- UID unico, Space nativo y Host muro;
- Placement y altura con relink a master A1;
- save/reopen;
- Undo/Redo de creacion, visibilidad y altura;
- DXF de exactamente dos PLAN;
- sincronizacion idempotente y cero huerfanos.

El FCStd y DXF temporales se eliminaron. MCP volvio a mostrar solamente el
documento productivo que ya estaba abierto, el cual no fue activado, guardado o
modificado. No se tocaron Upala, sus 48 tomacorrientes ni sus 11 apagadores.
No se hizo commit ni push.

## Integracion posterior en herramientas reales

La arquitectura A1 se reutilizo sin variantes en las dos macros productivas de
colocacion BIM. El opt-in es una casilla efimera, desmarcada y no persistida;
`LegacyCompound` sigue siendo el default. Ambas completan UID/Space/Host y PLAN
dentro de su transaccion existente. En modo A1, un apagador legacy coincidente
se preserva y no se actualiza.

La prueba `freecad_upala_real_placement_a1_smoke.py` aprobo por MCP con una toma
y un apagador A1 calculados por los helpers reales de muro y puerta. Verifico
forma fisica, PLAN, Host, Space/RoomResolver, PuertaOrigen, Placement,
altura/relink, save/reopen, Undo/Redo, DXF e invariancia frente a sincronizacion
PLAN. El original se comparo por SHA-256 y tamano y quedo intacto; no quedaron
temporales.

Evidencia importante para retomar: Drive conserva el arbol historico de 48
tomas y 11 apagadores, pero el FCStd vigente habia vuelto a 187 objetos y cero
dispositivos durante la prueba. `Apagador - Rectangle006` enlazaba realmente a
la puerta `Window`, al muro `Wall` y al area auxiliar `Rectangle006`; el Label
nombraba el area, no una puerta. Su Placement historico estaba en el origen de
la puerta y difiere del offset de jamba vigente. No corregir sin recuperar una
fuente que permita atribuir la causa.
